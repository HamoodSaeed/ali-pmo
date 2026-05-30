import { type FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  CreditCard,
  Download,
  FileSpreadsheet,
  FileText,
  FolderKanban,
  Home,
  Layers3,
  Loader2,
  ShieldCheck,
  UploadCloud
} from "lucide-react";
import { api, getBillingEmail, setBillingEmail, uploadDocument } from "./api";
import type { Analysis, BillingConfig, BillingStatus, CheckoutPayload, OutputFile, ParseResult, PlanTask, ProjectMetadata, ProjectPlan } from "./types";

type Page = "dashboard" | "billing" | "upload" | "intelligence" | "plan" | "outputs";
type BusyAction = "upload" | "parse" | "analyze" | "plan" | "outputs" | "checkout" | "confirm" | null;

const navigation: Array<{ page: Page; label: string; icon: typeof Home }> = [
  { page: "dashboard", label: "Dashboard", icon: Home },
  { page: "billing", label: "Billing", icon: CreditCard },
  { page: "upload", label: "Upload", icon: UploadCloud },
  { page: "intelligence", label: "Intelligence", icon: Layers3 },
  { page: "plan", label: "Project Plan", icon: BarChart3 },
  { page: "outputs", label: "Output Center", icon: Download }
];

function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [projects, setProjects] = useState<ProjectMetadata[]>([]);
  const [currentProject, setCurrentProject] = useState<ProjectMetadata | null>(null);
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [plan, setPlan] = useState<ProjectPlan | null>(null);
  const [outputs, setOutputs] = useState<OutputFile[]>([]);
  const [busyAction, setBusyAction] = useState<BusyAction>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [message, setMessage] = useState("Ready for project intake.");
  const [error, setError] = useState<string | null>(null);
  const [billingConfig, setBillingConfig] = useState<BillingConfig | null>(null);
  const [billingStatus, setBillingStatus] = useState<BillingStatus | null>(null);

  useEffect(() => {
    initializeApp();
  }, []);

  const billingLocked = Boolean(billingConfig?.payment_required && !billingStatus?.active);
  const canUseProject = Boolean(currentProject) && !billingLocked;
  const escalations = useMemo(() => {
    const riskCount = analysis?.risks.filter((risk) => risk.escalation_required).length ?? 0;
    const dependencyCount = analysis?.dependencies.filter((dependency) => dependency.escalation_required).length ?? 0;
    return riskCount + dependencyCount;
  }, [analysis]);

  async function initializeApp() {
    await refreshBilling();
    const params = new URLSearchParams(window.location.search);
    if (params.get("payment") === "return") {
      await confirmPaymentReturn(params);
      return;
    }
    await refreshProjects();
  }

  async function refreshBilling(email = getBillingEmail()) {
    try {
      const [config, status] = await Promise.all([api.billingConfig(), api.billingStatus(email || undefined)]);
      setBillingConfig(config);
      setBillingStatus(status);
      if (config.payment_required && !status.active) {
        setMessage("Subscription required before project processing.");
      }
      return { config, status };
    } catch (err) {
      setError(readError(err));
      return null;
    }
  }

  async function confirmPaymentReturn(params: URLSearchParams) {
    const provider = params.get("provider");
    const tapId = params.get("tap_id");
    const email = params.get("email") || getBillingEmail();
    if (provider === "lemonsqueezy" && email) {
      setBillingEmail(email);
      window.history.replaceState({}, "", window.location.pathname);
      const result = await refreshBilling(email);
      setPage(result?.status.active ? "upload" : "billing");
      setMessage(result?.status.active ? "Subscription active. You can upload project documents now." : "Payment received. Refresh status shortly while Lemon Squeezy confirms the subscription.");
      if (result?.status.active) await refreshProjects();
      return;
    }
    if (!tapId || !email) {
      setPage("billing");
      setError("Payment return is missing Tap transaction details.");
      return;
    }

    setBusyAction("confirm");
    setMessage("Confirming Tap payment...");
    try {
      setBillingEmail(email);
      const result = await api.confirmBilling(tapId, email);
      setBillingStatus(result);
      setMessage("Subscription active. You can upload project documents now.");
      window.history.replaceState({}, "", window.location.pathname);
      setPage("upload");
      await refreshProjects();
    } catch (err) {
      setError(readError(err));
      setPage("billing");
    } finally {
      setBusyAction(null);
    }
  }

  async function refreshProjects() {
    if (billingConfig?.payment_required && !billingStatus?.active) {
      setProjects([]);
      return;
    }
    try {
      const result = await api.projects();
      setProjects(result.projects);
      if (!currentProject && result.projects.length > 0) {
        setCurrentProject(result.projects[0]);
      }
    } catch (err) {
      setError(readError(err));
    }
  }

  async function loadProject(fileId: string) {
    if (billingLocked) {
      setPage("billing");
      return;
    }
    try {
      setBusyAction("parse");
      const snapshot = await api.snapshot(fileId);
      setCurrentProject(snapshot.metadata);
      setAnalysis(snapshot.analysis);
      setPlan(snapshot.plan);
      setOutputs(snapshot.metadata.outputs ?? []);
      setParseResult(null);
      setMessage(`Loaded ${snapshot.metadata.original_filename}`);
      setPage(snapshot.plan ? "plan" : snapshot.analysis ? "intelligence" : "upload");
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleUpload(file: File) {
    if (billingLocked) {
      setPage("billing");
      return;
    }
    setError(null);
    setBusyAction("upload");
    setUploadProgress(0);
    setMessage("Uploading document...");
    try {
      const result = await uploadDocument(file, setUploadProgress);
      setCurrentProject(result.metadata);
      setParseResult(null);
      setAnalysis(null);
      setPlan(null);
      setOutputs([]);
      setMessage("Upload complete. Parse the document to create a text cache.");
      setPage("upload");
      await refreshProjects();
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusyAction(null);
    }
  }

  async function runParse() {
    if (!currentProject || billingLocked) return;
    setBusyAction("parse");
    setError(null);
    setMessage("Extracting text and saving cache...");
    try {
      const result = await api.parse(currentProject.file_id);
      setParseResult(result);
      setMessage(result.cached ? "Using existing text cache." : "Parsing complete. Text cache saved.");
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusyAction(null);
    }
  }

  async function runAnalyze() {
    if (!currentProject || billingLocked) return;
    setBusyAction("analyze");
    setError(null);
    setMessage("Identifying PMO structure...");
    try {
      const result = await api.analyze(currentProject.file_id);
      setAnalysis(result);
      setMessage("Project intelligence generated.");
      setPage("intelligence");
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusyAction(null);
    }
  }

  async function runPlan() {
    if (!currentProject || billingLocked) return;
    setBusyAction("plan");
    setError(null);
    setMessage("Generating WBS and schedule assumptions...");
    try {
      const result = await api.generatePlan(currentProject.file_id);
      setPlan(result);
      setMessage("Project plan generated.");
      setPage("plan");
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusyAction(null);
    }
  }

  async function runOutputs() {
    if (!currentProject || billingLocked) return;
    setBusyAction("outputs");
    setError(null);
    setMessage("Building export files...");
    try {
      const result = await api.generateOutputs(currentProject.file_id);
      setOutputs(result.outputs);
      setMessage("All output files are ready for download.");
      setPage("outputs");
      await refreshProjects();
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusyAction(null);
    }
  }

  async function startCheckout(payload: CheckoutPayload) {
    setBusyAction("checkout");
    setError(null);
    setMessage("Creating secure checkout...");
    try {
      setBillingEmail(payload.email);
      const result = await api.createCheckout(payload);
      window.location.href = result.checkout_url;
    } catch (err) {
      setError(readError(err));
      setMessage("Checkout could not be created.");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">AP</div>
          <div>
            <h1>Ali PMO</h1>
            <p>Project control OS</p>
          </div>
        </div>

        <nav>
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <button key={item.page} className={page === item.page ? "nav-item active" : "nav-item"} onClick={() => setPage(item.page)}>
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-status">
          <span className="status-dot" />
          <p>{message}</p>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">Intelligent Project Management Operating System</p>
            <h2>{currentProject ? currentProject.original_filename : "Executive project intake"}</h2>
          </div>
          <div className="topbar-actions">
            {escalations > 0 && (
              <span className="escalation-pill">
                <AlertTriangle size={16} />
                {escalations} escalation{escalations > 1 ? "s" : ""}
              </span>
            )}
            <button className="secondary-button" onClick={refreshProjects}>
              Refresh
            </button>
            <button className={billingLocked ? "payment-button due" : "payment-button"} onClick={() => setPage("billing")}>
              {billingStatus?.active ? <ShieldCheck size={16} /> : <CreditCard size={16} />}
              {billingStatus?.active ? "Active" : billingConfig ? `${billingConfig.amount.toFixed(2)} ${billingConfig.currency}/month` : "Monthly access"}
            </button>
          </div>
        </header>

        {error && (
          <div className="alert">
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        )}

        {page === "dashboard" && (
          <Dashboard projects={projects} onUpload={() => setPage(billingLocked ? "billing" : "upload")} onOpenProject={loadProject} billingLocked={billingLocked} />
        )}
        {page === "billing" && <BillingPage config={billingConfig} status={billingStatus} busyAction={busyAction} onCheckout={startCheckout} onRefresh={refreshBilling} />}
        {page === "upload" && (
          <UploadPage
            currentProject={currentProject}
            parseResult={parseResult}
            busyAction={busyAction}
            uploadProgress={uploadProgress}
            onUpload={handleUpload}
            onParse={runParse}
            onAnalyze={runAnalyze}
            onPlan={runPlan}
            onOutputs={runOutputs}
            canUseProject={canUseProject}
            billingLocked={billingLocked}
            onBilling={() => setPage("billing")}
          />
        )}
        {page === "intelligence" && <IntelligencePage analysis={analysis} onGeneratePlan={runPlan} busyAction={busyAction} />}
        {page === "plan" && <PlanPage plan={plan} onGenerateOutputs={runOutputs} busyAction={busyAction} fileId={currentProject?.file_id} outputs={outputs} />}
        {page === "outputs" && <OutputCenter outputs={outputs} fileId={currentProject?.file_id} onGenerateOutputs={runOutputs} busyAction={busyAction} />}
      </main>
    </div>
  );
}

function Dashboard({
  projects,
  onUpload,
  onOpenProject,
  billingLocked
}: {
  projects: ProjectMetadata[];
  onUpload: () => void;
  onOpenProject: (fileId: string) => void;
  billingLocked: boolean;
}) {
  return (
    <section className="page-grid">
      <div className="hero-panel">
        <div>
          <p className="eyebrow">Ali PMO</p>
          <h3>Intelligent Project Management Operating System</h3>
          <p>
            Upload messy project documents and generate PMO-ready project plans, RAID logs, executive summaries, weekly updates, and Microsoft Project XML.
          </p>
        </div>
        <button className="primary-button" onClick={onUpload}>
          {billingLocked ? <CreditCard size={18} /> : <UploadCloud size={18} />}
          {billingLocked ? "Subscribe to start" : "Upload document"}
        </button>
      </div>

      <div className="content-section">
        <div className="section-heading">
          <h3>Recent projects</h3>
          <span>{projects.length} stored</span>
        </div>
        <div className="project-list">
          {projects.length === 0 && <EmptyState title="No documents uploaded" description="Start with a PDF or TXT project brief." />}
          {projects.map((project) => (
            <button className="project-row" key={project.file_id} onClick={() => onOpenProject(project.file_id)}>
              <FileText size={20} />
              <div>
                <strong>{project.original_filename}</strong>
                <span>
                  {project.parser_status} · {formatBytes(project.size_bytes)}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

function UploadPage(props: {
  currentProject: ProjectMetadata | null;
  parseResult: ParseResult | null;
  busyAction: BusyAction;
  uploadProgress: number;
  onUpload: (file: File) => void;
  onParse: () => void;
  onAnalyze: () => void;
  onPlan: () => void;
  onOutputs: () => void;
  canUseProject: boolean;
  billingLocked: boolean;
  onBilling: () => void;
}) {
  const [isDragging, setIsDragging] = useState(false);

  function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (file) props.onUpload(file);
  }

  return (
    <section className="page-grid">
      {props.billingLocked && <BillingRequiredNotice onBilling={props.onBilling} />}
      <div
        className={isDragging ? "dropzone dragging" : "dropzone"}
        onDragEnter={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          handleFiles(event.dataTransfer.files);
        }}
      >
        <UploadCloud size={42} />
        <h3>Upload a project document</h3>
        <p>PDF and TXT are fully supported in this prototype. DOCX, CSV, and XLSX have basic extraction support.</p>
        <label className="primary-button file-picker">
          Select file
          <input type="file" accept=".pdf,.txt,.docx,.csv,.xlsx" disabled={props.billingLocked} onChange={(event) => handleFiles(event.target.files)} />
        </label>
        {props.busyAction === "upload" && (
          <div className="progress-track">
            <span style={{ width: `${props.uploadProgress}%` }} />
          </div>
        )}
      </div>

      <div className="control-panel">
        <div className="section-heading">
          <h3>Processing controls</h3>
          {props.currentProject && <span>{props.currentProject.extension.toUpperCase()}</span>}
        </div>
        <div className="step-actions">
          <ActionButton label="Parse document" icon={FileText} busy={props.busyAction === "parse"} disabled={!props.canUseProject} onClick={props.onParse} />
          <ActionButton label="Analyze project content" icon={Layers3} busy={props.busyAction === "analyze"} disabled={!props.canUseProject} onClick={props.onAnalyze} />
          <ActionButton label="Generate project plan" icon={BarChart3} busy={props.busyAction === "plan"} disabled={!props.canUseProject} onClick={props.onPlan} />
          <ActionButton label="Generate outputs" icon={FileSpreadsheet} busy={props.busyAction === "outputs"} disabled={!props.canUseProject} onClick={props.onOutputs} />
        </div>
      </div>

      {props.parseResult && (
        <div className="content-section wide">
          <div className="section-heading">
            <h3>Extraction preview</h3>
            <span>
              {props.parseResult.page_count} page · {props.parseResult.character_count.toLocaleString()} chars
            </span>
          </div>
          <pre className="preview">{props.parseResult.preview_text}</pre>
        </div>
      )}
    </section>
  );
}

function BillingRequiredNotice({ onBilling }: { onBilling: () => void }) {
  return (
    <div className="notice wide billing-notice">
      <CreditCard size={18} />
      <span>Ali PMO processing is locked until the user has an active monthly subscription.</span>
      <button className="secondary-button" onClick={onBilling}>
        Manage billing
      </button>
    </div>
  );
}

function BillingPage({
  config,
  status,
  busyAction,
  onCheckout,
  onRefresh
}: {
  config: BillingConfig | null;
  status: BillingStatus | null;
  busyAction: BusyAction;
  onCheckout: (payload: CheckoutPayload) => void;
  onRefresh: (email?: string) => Promise<unknown>;
}) {
  const [email, setEmail] = useState(status?.email ?? getBillingEmail());
  const [firstName, setFirstName] = useState("Ali");
  const [lastName, setLastName] = useState("PMO User");
  const [phoneCountryCode, setPhoneCountryCode] = useState("968");
  const [phoneNumber, setPhoneNumber] = useState("");

  const active = Boolean(status?.active);
  const amount = config ? `${config.amount.toFixed(2)} ${config.currency}` : "Monthly access";
  const providerName = config?.provider === "lemonsqueezy" ? "Lemon Squeezy" : "Tap";

  function submitCheckout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onCheckout({
      email,
      first_name: firstName,
      last_name: lastName,
      phone_country_code: phoneCountryCode,
      phone_number: phoneNumber || undefined
    });
  }

  async function checkStatus(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBillingEmail(email);
    await onRefresh(email);
  }

  return (
    <section className="page-grid">
      <div className="content-section billing-panel">
        <p className="eyebrow">Ali PMO monthly access</p>
        <h3>{amount} per user per month</h3>
        <p>
          {providerName} hosted checkout keeps card entry outside Ali PMO. Access is unlocked only after the payment provider confirms the subscription.
        </p>
        <div className={active ? "subscription-state active" : "subscription-state"}>
          {active ? <ShieldCheck size={22} /> : <CreditCard size={22} />}
          <div>
            <strong>{active ? "Subscription active" : "Subscription required"}</strong>
            <span>{status?.subscription?.current_period_end ? `Renews/checks again ${status.subscription.current_period_end.slice(0, 10)}` : "Monthly plan"}</span>
          </div>
        </div>
      </div>

      <div className="control-panel">
        <div className="section-heading">
          <h3>{providerName} checkout</h3>
          <span>{config?.tap_configured ? "Configured" : "Needs key"}</span>
        </div>
        <form className="billing-form" onSubmit={submitCheckout}>
          <label>
            Email
            <input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label>
            First name
            <input required value={firstName} onChange={(event) => setFirstName(event.target.value)} />
          </label>
          <label>
            Last name
            <input required value={lastName} onChange={(event) => setLastName(event.target.value)} />
          </label>
          <div className="split-inputs">
            <label>
              Country code
              <input value={phoneCountryCode} onChange={(event) => setPhoneCountryCode(event.target.value)} />
            </label>
            <label>
              Phone
              <input inputMode="tel" placeholder="9xxxxxxx" value={phoneNumber} onChange={(event) => setPhoneNumber(event.target.value)} />
            </label>
          </div>
          <button className="primary-button" disabled={!config?.tap_configured || busyAction === "checkout"}>
            {busyAction === "checkout" ? <Loader2 className="spin" size={18} /> : <CreditCard size={18} />}
            Pay {amount}
          </button>
        </form>
        {!config?.tap_configured && <p className="form-note">Billing setup is incomplete. Add the provider credentials on the backend.</p>}
      </div>

      <div className="content-section wide">
        <div className="section-heading">
          <h3>Check subscription</h3>
          <span>{status?.email ?? "No email saved"}</span>
        </div>
        <form className="status-form" onSubmit={checkStatus}>
          <input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
          <button className="secondary-button" disabled={busyAction === "confirm"}>
            Refresh status
          </button>
        </form>
      </div>
    </section>
  );
}

function IntelligencePage({ analysis, onGeneratePlan, busyAction }: { analysis: Analysis | null; onGeneratePlan: () => void; busyAction: BusyAction }) {
  if (!analysis) {
    return <EmptyState title="No intelligence generated yet" description="Upload and analyze a document to populate PMO control sections." />;
  }

  return (
    <section className="page-grid">
      <div className="content-section wide">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Project intelligence</p>
            <h3>{analysis.project_title}</h3>
          </div>
          <button className="primary-button" onClick={onGeneratePlan} disabled={busyAction === "plan"}>
            {busyAction === "plan" ? <Loader2 className="spin" size={18} /> : <BarChart3 size={18} />}
            Generate plan
          </button>
        </div>

        <div className="intel-grid">
          <InfoCard title="Scope" items={analysis.scope} />
          <InfoCard title="Objectives" items={analysis.objectives} />
          <InfoCard title="Deliverables" items={analysis.deliverables} />
          <InfoCard title="Milestones" items={analysis.milestones} />
          <InfoCard title="Risks" items={analysis.risks.map((risk) => risk.description)} tone="risk" />
          <InfoCard title="Dependencies" items={analysis.dependencies.map((dependency) => dependency.description)} tone="dependency" />
          <InfoCard title="Stakeholders" items={analysis.stakeholders.map((stakeholder) => `${stakeholder.name} · ${stakeholder.role}`)} />
          <InfoCard title="Missing Information" items={analysis.missing_information} tone="missing" />
        </div>
      </div>
    </section>
  );
}

function PlanPage(props: { plan: ProjectPlan | null; onGenerateOutputs: () => void; busyAction: BusyAction; fileId?: string; outputs: OutputFile[] }) {
  if (!props.plan) {
    return <EmptyState title="No project plan generated" description="Generate a plan after analysis to see WBS, dates, owners, dependencies, and status." />;
  }

  return (
    <section className="page-grid">
      <div className="content-section wide">
        <div className="section-heading">
          <div>
            <p className="eyebrow">WBS control table</p>
            <h3>{props.plan.project_title}</h3>
          </div>
          <button className="primary-button" onClick={props.onGenerateOutputs} disabled={props.busyAction === "outputs"}>
            {props.busyAction === "outputs" ? <Loader2 className="spin" size={18} /> : <Download size={18} />}
            Generate outputs
          </button>
        </div>
        {props.plan.assumptions.length > 0 && (
          <div className="notice">
            <CheckCircle2 size={18} />
            <span>{props.plan.assumptions.join(" ")}</span>
          </div>
        )}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>WBS</th>
                <th>Task</th>
                <th>Start</th>
                <th>End</th>
                <th>Duration</th>
                <th>Owner</th>
                <th>Dependency</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {props.plan.tasks.map((task) => (
                <PlanRow key={`${task.wbs_id}-${task.task_name}`} task={task} />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {props.outputs.length > 0 && <OutputStrip outputs={props.outputs} fileId={props.fileId} />}
    </section>
  );
}

function OutputCenter({ outputs, fileId, onGenerateOutputs, busyAction }: { outputs: OutputFile[]; fileId?: string; onGenerateOutputs: () => void; busyAction: BusyAction }) {
  return (
    <section className="page-grid">
      <div className="content-section wide">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Download center</p>
            <h3>Generated project control outputs</h3>
          </div>
          <button className="primary-button" onClick={onGenerateOutputs} disabled={!fileId || busyAction === "outputs"}>
            {busyAction === "outputs" ? <Loader2 className="spin" size={18} /> : <FileSpreadsheet size={18} />}
            Regenerate
          </button>
        </div>
        {outputs.length === 0 ? (
          <EmptyState title="No outputs generated yet" description="Generate outputs from the project plan to download Excel, CSV, RAID, summary, status, and XML files." />
        ) : (
          <div className="output-grid">
            {outputs.map((output) => (
              <a className="output-card" href={fileId ? api.downloadUrl(fileId, output.name) : "#"} key={output.name}>
                <Download size={22} />
                <strong>{output.name}</strong>
                <span>{formatBytes(output.size_bytes)}</span>
              </a>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function InfoCard({ title, items, tone }: { title: string; items: string[]; tone?: "risk" | "dependency" | "missing" }) {
  return (
    <article className={`info-card ${tone ?? ""}`}>
      <h4>{title}</h4>
      {items.length === 0 ? (
        <p className="muted">TBD</p>
      ) : (
        <ul>
          {items.slice(0, 10).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </article>
  );
}

function PlanRow({ task }: { task: PlanTask }) {
  const isSummary = !task.wbs_id.includes(".") && !task.wbs_id.startsWith("M");
  return (
    <tr className={isSummary ? "summary-row" : ""}>
      <td>{task.wbs_id}</td>
      <td>
        <strong>{task.task_name}</strong>
        {task.milestone && <span className="mini-pill">Milestone</span>}
      </td>
      <td>{task.start_date}</td>
      <td>{task.end_date}</td>
      <td>{task.duration}</td>
      <td>{task.owner}</td>
      <td>{task.dependency_predecessor || "None"}</td>
      <td>
        <span className={`status-chip ${task.status.toLowerCase().replace(/\s+/g, "-")}`}>{task.status}</span>
      </td>
    </tr>
  );
}

function OutputStrip({ outputs, fileId }: { outputs: OutputFile[]; fileId?: string }) {
  return (
    <div className="output-strip">
      {outputs.map((output) => (
        <a href={fileId ? api.downloadUrl(fileId, output.name) : "#"} key={output.name}>
          <Download size={16} />
          {output.name}
        </a>
      ))}
    </div>
  );
}

function ActionButton(props: { label: string; icon: typeof FileText; busy: boolean; disabled: boolean; onClick: () => void }) {
  const Icon = props.icon;
  return (
    <button className="action-button" disabled={props.disabled || props.busy} onClick={props.onClick}>
      {props.busy ? <Loader2 className="spin" size={20} /> : <Icon size={20} />}
      <span>{props.label}</span>
    </button>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="empty-state">
      <FolderKanban size={36} />
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function readError(err: unknown) {
  return err instanceof Error ? err.message : "Unexpected error";
}

export default App;
