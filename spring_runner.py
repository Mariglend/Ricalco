"""Esecuzione reale di esercizi Spring Boot / JUnit con Maven.

Il progetto modello vive in data/spring/ e viene compilato ed eseguito con `mvn test`.
La prima preparazione scarica Maven (se manca) e le librerie Spring da Maven Central (~150 MB).
"""
import glob
import io
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

SPRING_BOOT = "3.5.0"
MAVEN_VERSION = "3.9.9"
MAVEN_URL = (f"https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/{MAVEN_VERSION}/"
             f"apache-maven-{MAVEN_VERSION}-bin.zip")
PKG = "com.ricalco.app"
PKG_DIR = PKG.replace(".", "/")
RUN_TIMEOUT = 240
NOWINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

POM_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>@BOOT@</version>
    <relativePath/>
  </parent>
  <groupId>com.ricalco</groupId>
  <artifactId>esercizi</artifactId>
  <version>1.0</version>
  <properties>
    <java.version>17</java.version>
    <maven.compiler.release>17</maven.compiler.release>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>
@MGMT@  <dependencies>
    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency>
    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-data-jpa</artifactId></dependency>
    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-validation</artifactId></dependency>
    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-jdbc</artifactId></dependency>
    <dependency><groupId>com.h2database</groupId><artifactId>h2</artifactId><scope>runtime</scope></dependency>
    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-test</artifactId><scope>test</scope></dependency>
@DEPS@  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>
        <configuration>
          <argLine>-Dnet.bytebuddy.experimental=true -XX:+EnableDynamicAgentLoading -Xshare:off</argLine>
          <trimStackTrace>true</trimStackTrace>
          <redirectTestOutputToFile>true</redirectTestOutputToFile>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
"""

def make_pom(deps="", mgmt=""):
    return POM_TEMPLATE.replace("@BOOT@", SPRING_BOOT).replace("@DEPS@", deps).replace("@MGMT@", mgmt)


POM = make_pom()

APP = f"""package {PKG};

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class App {{
    public static void main(String[] args) {{
        SpringApplication.run(App.class, args);
    }}
}}
"""

PROPS = """spring.main.banner-mode=off
logging.level.root=WARN
spring.jpa.open-in-view=false
spring.datasource.url=jdbc:h2:mem:esercizi;DB_CLOSE_DELAY=-1
spring.jpa.hibernate.ddl-auto=create-drop
"""

SAMPLE_CODE = """import org.springframework.web.bind.annotation.*;

@RestController
public class SalutoController {
    @GetMapping("/ciao/{nome}")
    public String ciao(@PathVariable String nome) {
        return "Ciao " + nome;
    }
}
"""

SAMPLE_TEST = """import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class EsercizioTest {
    @Autowired
    MockMvc mvc;

    @Test
    void salutaPerNome() throws Exception {
        mvc.perform(get("/ciao/Ada")).andExpect(status().isOk()).andExpect(content().string("Ciao Ada"));
    }
}
"""


class SpringRunner:
    java_home = None   # il JDK da dare a Maven (lo sceglie il server: il più recente con javac)

    def env(self):
        e = dict(os.environ)
        if SpringRunner.java_home:
            e["JAVA_HOME"] = SpringRunner.java_home
            e["PATH"] = str(Path(SpringRunner.java_home) / "bin") + os.pathsep + e.get("PATH", "")
        return e

    def __init__(self, data_dir, name="spring", deps="", mgmt="", sample=None, label="Spring Boot", parent=None):
        """name: cartella in data/; deps/mgmt: dipendenze in più nel pom; parent: il runner base (Maven e preparazione in comune)."""
        self.base = Path(data_dir) / name
        self.tools = Path(data_dir) / "tools"
        self.pom = make_pom(deps, mgmt)
        self.sample = sample or (SAMPLE_CODE, SAMPLE_TEST)
        self.label = label
        self.parent = parent
        self.children = []
        if parent:
            parent.children.append(self)
        self.lock = threading.RLock()  # run() si richiama da solo (offline → online) dentro il lock
        self.state_file = self.base / "pronto.txt"
        self.log = []
        self.busy = False

    # ---------------------------------------------------------- stato
    def mvn_path(self):
        local = self.tools / f"apache-maven-{MAVEN_VERSION}" / "bin" / ("mvn.cmd" if os.name == "nt" else "mvn")
        if local.exists():
            return str(local)
        for name in ("mvn.cmd", "mvn"):
            p = shutil.which(name)
            if p:
                return p
        return None

    def ready(self):
        if self.parent:
            return self.parent.ready()
        return self.state_file.exists() and bool(self.mvn_path())

    def status(self):
        return {"ready": self.ready(), "maven": self.mvn_path(), "busy": self.busy, "log": self.log[-30:],
                "springBoot": SPRING_BOOT, "extras": [{"label": c.label, "ready": c.state_file.exists()} for c in self.children]}

    # ---------------------------------------------------------- preparazione
    def _say(self, msg):
        self.log.append(msg)
        self.log = self.log[-200:]

    def write_template(self):
        (self.base / "src/main/java" / PKG_DIR).mkdir(parents=True, exist_ok=True)
        (self.base / "src/main/resources").mkdir(parents=True, exist_ok=True)
        (self.base / "src/test/java" / PKG_DIR).mkdir(parents=True, exist_ok=True)
        (self.base / "pom.xml").write_text(self.pom, encoding="utf-8")
        (self.base / "src/main/resources/application.properties").write_text(PROPS, encoding="utf-8")

    def download_maven(self):
        self._say(f"Scarico Maven {MAVEN_VERSION} (circa 9 MB)…")
        self.tools.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(MAVEN_URL, timeout=120) as r:
            data = r.read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            z.extractall(self.tools)
        if os.name != "nt":
            for f in glob.glob(str(self.tools / f"apache-maven-{MAVEN_VERSION}" / "bin" / "*")):
                os.chmod(f, 0o755)
        self._say("Maven installato.")

    def setup(self):
        """Prepara tutto: Maven, progetto, librerie. Lungo la prima volta (scarica le dipendenze)."""
        if self.busy:
            return {"ok": False, "error": "Preparazione già in corso."}
        self.busy = True
        self.log = []
        try:
            if not self.mvn_path():
                self.download_maven()
            self.write_template()
            self._say("Scarico Spring Boot e le librerie di test (la prima volta 2-5 minuti)…")
            res = self.run(*self.sample, offline=False, timeout=900, setup=True)
            if res.get("all_ok"):
                self.state_file.write_text(time.strftime("%Y-%m-%d %H:%M"), encoding="utf-8")
                self._say("Fatto: i test Spring girano sul tuo PC.")
                for ch in self.children:
                    self._say(f"Scarico le librerie di {ch.label} (la prima volta 1-3 minuti)…")
                    r = ch.run(*ch.sample, offline=False, timeout=900, setup=True)
                    if r.get("all_ok"):
                        self._say(f"Pronto anche {ch.label}.")
                    else:
                        self._say(f"{ch.label} non è pronto: " + (r.get("error") or "test di prova falliti")[:400])
                return {"ok": True}
            self._say("La prova non è passata: " + (res.get("error") or "test falliti"))
            return {"ok": False, "error": res.get("error") or "Il test di prova non è passato."}
        except Exception as e:
            self._say("Errore: " + str(e))
            return {"ok": False, "error": str(e)}
        finally:
            self.busy = False

    # ---------------------------------------------------------- codice → file
    @staticmethod
    def split_types(code):
        """Divide il codice dello studente in un file per ogni tipo di primo livello.
        Restituisce (imports, [(nome, start_line, testo)]) con numeri di riga del codice originale."""
        lines = code.replace("\r\n", "\n").split("\n")
        imports = []
        body = []
        for ln in lines:
            if re.match(r"\s*import\s+[\w.*]+\s*;\s*$", ln) or re.match(r"\s*import\s+static\s+[\w.*]+\s*;\s*$", ln):
                imports.append(ln.strip())
                body.append("")
            elif re.match(r"\s*package\s+[\w.]+\s*;\s*$", ln):
                body.append("")
            else:
                body.append(ln)
        decl = re.compile(r"^(?:(?:public|abstract|final|sealed|non-sealed|static)\s+)*(class|interface|enum|record|@interface)\s+(\w+)")
        starts = []
        for i, ln in enumerate(body):
            if ln[:1] not in (" ", "\t", "}", "") and decl.match(ln):
                j = i
                while j > 0 and body[j - 1].startswith("@"):
                    j -= 1
                starts.append((j, decl.match(ln).group(2)))
        if not starts:
            return imports, [("Codice", 0, "\n".join(body))]
        chunks = []
        for k, (s, name) in enumerate(starts):
            e = starts[k + 1][0] if k + 1 < len(starts) else len(body)
            s0 = s if k else 0
            chunks.append((name, s0, "\n".join(body[s0:e])))
        return imports, chunks

    def _write_sources(self, code, test):
        main_dir = self.base / "src/main/java" / PKG_DIR
        test_dir = self.base / "src/test/java" / PKG_DIR
        for d in (main_dir, test_dir):
            for f in d.glob("*.java"):
                if f.name != "App.java":
                    f.unlink()
        (main_dir / "App.java").write_text(APP, encoding="utf-8")
        mapping = {}
        imports, chunks = self.split_types(code)
        head = [f"package {PKG};", ""] + imports + [""]
        for name, start, text in chunks:
            if name == "App":
                continue
            fname = f"{name}.java"
            text = re.sub(r"^(\s*)(?:public\s+)?((?:abstract\s+|final\s+)*(?:class|interface|enum|record)\s+" + re.escape(name) + r"\b)",
                          r"\1public \2", text, count=1, flags=re.M)
            (main_dir / fname).write_text("\n".join(head) + "\n" + text + "\n", encoding="utf-8")
            mapping[fname] = ("main", len(head) + 1, start)
        timports, tchunks = self.split_types(test)
        thead = [f"package {PKG};", ""] + timports + [""]
        for name, start, text in tchunks:
            fname = f"{name}.java"
            (test_dir / fname).write_text("\n".join(thead) + "\n" + text + "\n", encoding="utf-8")
            mapping[fname] = ("test", len(thead) + 1, start)
        return mapping

    # ---------------------------------------------------------- esecuzione
    def run(self, code, test, offline=True, timeout=RUN_TIMEOUT, setup=False):
        mvn = self.mvn_path()
        if not mvn:
            return {"error": "Maven non è installato: prepara Spring dalla pagina «Prova il modello».", "tests": []}
        if self.parent and not self.state_file.exists():
            timeout = max(timeout, 900)  # la prima volta scarica le librerie in più
        with self.lock:
            pom = self.base / "pom.xml"
            if not pom.exists() or pom.read_text(encoding="utf-8") != self.pom:
                self.write_template()
            mapping = self._write_sources(code, test)
            rep = self.base / "target" / "surefire-reports"
            if rep.exists():
                shutil.rmtree(rep, ignore_errors=True)
            cmd = [mvn, "-B", "--no-transfer-progress", "clean", "test"]
            if offline:
                cmd.insert(1, "-o")
            if os.name == "nt" and mvn.lower().endswith((".cmd", ".bat")):
                cmd = ["cmd", "/c"] + cmd
            t0 = time.time()
            try:
                p = subprocess.run(cmd, cwd=str(self.base), capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   timeout=timeout, stdin=subprocess.DEVNULL, creationflags=NOWINDOW, shell=False, env=self.env())
                out = (p.stdout or "") + "\n" + (p.stderr or "")
            except subprocess.TimeoutExpired:
                return {"error": "Tempo scaduto: Maven non ha finito in tempo (ciclo infinito o prima compilazione molto lenta).", "tests": []}
            except OSError as e:
                return {"error": f"Non riesco ad avviare Maven: {e}", "tests": []}
            secs = round(time.time() - t0, 1)
            if offline and ("offline mode" in out.lower() or "could not resolve" in out.lower()) and not rep.exists():
                return self.run(code, test, offline=False, timeout=timeout)
            if setup:
                for ln in out.splitlines():
                    if "[ERROR]" in ln:
                        (self.parent or self)._say(ln.strip()[:300])
            res = self.parse(out, rep, mapping, secs)
            if self.parent and res.get("tests"):
                self.state_file.write_text(time.strftime("%Y-%m-%d %H:%M"), encoding="utf-8")
            return res

    def _cmd(self, *args, offline=True):
        mvn = self.mvn_path()
        cmd = [mvn, "-B", "--no-transfer-progress", *args]
        if offline:
            cmd.insert(1, "-o")
        if os.name == "nt" and mvn.lower().endswith((".cmd", ".bat")):
            cmd = ["cmd", "/c"] + cmd
        return cmd

    def run_project(self, folder, offline=True, timeout=600):
        """`mvn test` su un progetto vero (cartella con il suo pom.xml)."""
        if not self.mvn_path():
            return {"error": "Maven non è installato: prepara Spring dalla pagina «Prova il modello».", "tests": []}
        folder = Path(folder)
        rep = folder / "target" / "surefire-reports"
        if rep.exists():
            shutil.rmtree(rep, ignore_errors=True)
        t0 = time.time()
        try:
            p = subprocess.run(self._cmd("test", offline=offline), cwd=str(folder), capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=timeout, stdin=subprocess.DEVNULL,
                               creationflags=NOWINDOW, env=self.env())
            out = (p.stdout or "") + "\n" + (p.stderr or "")
        except subprocess.TimeoutExpired:
            return {"error": "Tempo scaduto: Maven non ha finito in tempo.", "tests": []}
        except OSError as e:
            return {"error": f"Non riesco ad avviare Maven: {e}", "tests": []}
        low = out.lower()
        if offline and ("offline mode" in low or "could not resolve" in low or "cannot access" in low) and not rep.exists():
            return self.run_project(folder, offline=False, timeout=timeout)
        return self.parse(out, rep, {}, round(time.time() - t0, 1))

    def start_app(self, folder):
        """Avvia l'API con `mvn spring-boot:run` in una console sua (si chiude con Ctrl+C)."""
        if not self.mvn_path():
            raise ValueError("Maven non è installato: prepara Spring dalla pagina «Prova il modello».")
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        log = open(Path(folder) / "avvio.log", "w", encoding="utf-8") if not flags else None
        subprocess.Popen(self._cmd("spring-boot:run", offline=False), cwd=str(folder), creationflags=flags, env=self.env(),
                         stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT if log else None)
        return True

    @staticmethod
    def humanize(name):
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name).replace("_", " ").strip()
        return s[:1].upper() + s[1:].lower() if s else name

    def parse(self, out, rep, mapping, secs):
        tests = []
        for f in sorted(glob.glob(str(rep / "TEST-*.xml"))):
            try:
                root = ET.parse(f).getroot()
            except ET.ParseError:
                continue
            for tc in root.iter("testcase"):
                name = tc.get("name", "test").split("(")[0]
                bad = tc.find("failure")
                if bad is None:
                    bad = tc.find("error")
                r = {"desc": self.humanize(name), "call": name, "expected": "", "ok": bad is None}
                if bad is not None:
                    msg = (bad.get("message") or (bad.text or "").strip().split("\n")[0])
                    r["error"] = re.sub(r"\s+", " ", msg)[:500]
                tests.append(r)
        if tests:
            return {"error": None, "tests": tests, "stdout": "", "secs": secs,
                    "all_ok": all(t["ok"] for t in tests)}
        # nessun report: errore di compilazione o di contesto
        errs = []
        for ln in out.splitlines():
            m = re.search(r"\[ERROR\]\s+(?:.*[\\/])?(\w+\.java):\[(\d+),(\d+)\]\s*(.*)", ln)
            if m:
                fname, line, col, msg = m.group(1), int(m.group(2)), m.group(3), m.group(4)
                where = f"{fname}, riga {line}"
                if fname in mapping:
                    kind, head_len, start = mapping[fname]
                    user_line = start + (line - head_len) + 1
                    where = f"riga {user_line} del tuo codice" if kind == "main" else f"nei test ({fname}, riga {line})"
                errs.append(f"{where}: {msg}")
        if errs:
            uniq = list(dict.fromkeys(errs))
            e = "\n".join(uniq[:6])
            if all(" nei test " in x or x.startswith("nei test") for x in uniq):
                e += ("\n\nL'errore è nei test: di solito vuol dire che hai cambiato il nome di una classe, di un metodo "
                      "o di un endpoint che i test usano.")
            return {"error": e, "tests": [], "stdout": "", "secs": secs, "all_ok": False}
        skip = ("Re-run Maven", "To see the full stack", "re-run Maven", "For more information", "Some problems were",
                "could not read 1 project")
        tail = [re.sub(r"\s*-> \[Help \d+\]", "", ln.replace("[ERROR]", "")).strip()
                for ln in out.splitlines() if "[ERROR]" in ln and not any(x in ln for x in skip)]
        tail = [ln for ln in tail if ln and not ln.startswith("[Help")]
        msg = "\n".join(tail[:8]) or out[-1500:]
        return {"error": "Maven non è riuscito a eseguire i test:\n" + msg[:2000], "tests": [], "stdout": "", "secs": secs, "all_ok": False}


# ---------------------------------------------------------------- runner con librerie in più
# Spring Security: in un progetto a parte, perché basta averla nel classpath per chiudere tutti gli endpoint.
SECURITY_DEPS = """    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-security</artifactId></dependency>
    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-oauth2-resource-server</artifactId></dependency>
    <dependency><groupId>org.springframework.security</groupId><artifactId>spring-security-test</artifactId><scope>test</scope></dependency>
"""

SECURITY_SAMPLE_CODE = """import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.bind.annotation.*;

@Configuration
class Sicurezza {
    @Bean
    SecurityFilterChain filtri(HttpSecurity http) throws Exception {
        http.authorizeHttpRequests(a -> a.requestMatchers("/pubblico").permitAll().anyRequest().authenticated())
            .httpBasic(Customizer.withDefaults());
        return http.build();
    }
}

@RestController
class PortaController {
    @GetMapping("/pubblico")
    String pubblico() { return "tutti"; }

    @GetMapping("/privato")
    String privato() { return "solo chi è autenticato"; }
}
"""

SECURITY_SAMPLE_TEST = """import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class EsercizioTest {
    @Autowired
    MockMvc mvc;

    @Test
    void ilPubblicoEApertoATutti() throws Exception {
        mvc.perform(get("/pubblico")).andExpect(status().isOk());
    }

    @Test
    void ilPrivatoSenzaLoginDa401() throws Exception {
        mvc.perform(get("/privato")).andExpect(status().isUnauthorized());
    }

    @Test
    @WithMockUser
    void ilPrivatoConUnUtenteDa200() throws Exception {
        mvc.perform(get("/privato")).andExpect(status().isOk());
    }
}
"""

# Spring AI: modelli finti nei test, così gli esercizi non dipendono da Ollama e danno sempre lo stesso risultato.
SPRING_AI = "1.0.0"
AI_MGMT = f"""  <dependencyManagement>
    <dependencies>
      <dependency><groupId>org.springframework.ai</groupId><artifactId>spring-ai-bom</artifactId><version>{SPRING_AI}</version><type>pom</type><scope>import</scope></dependency>
    </dependencies>
  </dependencyManagement>
"""
AI_DEPS = """    <dependency><groupId>org.springframework.ai</groupId><artifactId>spring-ai-client-chat</artifactId></dependency>
    <dependency><groupId>org.springframework.ai</groupId><artifactId>spring-ai-vector-store</artifactId></dependency>
    <dependency><groupId>io.projectreactor</groupId><artifactId>reactor-test</artifactId><scope>test</scope></dependency>
"""

AI_SAMPLE_CODE = """import java.util.List;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.model.Generation;
import org.springframework.ai.chat.prompt.Prompt;

class ModelloFinto implements ChatModel {
    @Override
    public ChatResponse call(Prompt prompt) {
        return new ChatResponse(List.of(new Generation(new AssistantMessage("Hai scritto: " + prompt.getContents()))));
    }
}

class Assistente {
    private final ChatClient chat;

    Assistente(ChatModel modello) {
        this.chat = ChatClient.builder(modello).build();
    }

    String chiedi(String domanda) {
        return chat.prompt().user(domanda).call().content();
    }
}
"""

AI_SAMPLE_TEST = """import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertTrue;

class EsercizioTest {
    @Test
    void ilChatClientPassaLaDomandaAlModello() {
        String risposta = new Assistente(new ModelloFinto()).chiedi("ciao");
        assertTrue(risposta.contains("ciao"), risposta);
    }
}
"""


def make_runners(data_dir):
    """Il runner base e quelli con le librerie in più, indicizzati per nome (come in curriculum: «runner»)."""
    base = SpringRunner(data_dir)
    sec = SpringRunner(data_dir, "spring-security", SECURITY_DEPS, sample=(SECURITY_SAMPLE_CODE, SECURITY_SAMPLE_TEST),
                       label="Spring Security", parent=base)
    ai = SpringRunner(data_dir, "spring-ai", AI_DEPS, AI_MGMT, sample=(AI_SAMPLE_CODE, AI_SAMPLE_TEST),
                      label=f"Spring AI {SPRING_AI}", parent=base)
    return {"": base, "security": sec, "ai": ai}
