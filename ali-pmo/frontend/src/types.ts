export type ProjectMetadata = {
  file_id: string;
  original_filename: string;
  stored_filename: string;
  extension: string;
  content_type?: string;
  size_bytes: number;
  uploaded_at: string;
  parser_status: "pending" | "parsing" | "completed" | "failed";
  page_count?: number;
  character_count?: number;
  outputs?: OutputFile[];
};

export type ParseResult = {
  file_id: string;
  page_count: number;
  character_count: number;
  extraction_status: string;
  cached: boolean;
  preview_text: string;
};

export type Risk = {
  id: string;
  description: string;
  owner: string;
  impact: string;
  probability: string;
  status: string;
  escalation_required: boolean;
  mitigation: string;
};

export type Dependency = {
  id: string;
  description: string;
  owner: string;
  status: string;
  escalation_required: boolean;
};

export type Stakeholder = {
  id: string;
  name: string;
  role: string;
  approval_required: boolean;
};

export type Analysis = {
  file_id: string;
  project_title: string;
  background: string;
  scope: string[];
  objectives: string[];
  deliverables: string[];
  milestones: string[];
  tasks: Array<Record<string, unknown>>;
  risks: Risk[];
  assumptions: string[];
  dependencies: Dependency[];
  constraints: string[];
  stakeholders: Stakeholder[];
  dates: string[];
  acceptance_criteria: string[];
  required_approvals: string[];
  missing_information: string[];
  confidence_notes: string[];
};

export type PlanTask = {
  wbs_id: string;
  phase: string;
  task_name: string;
  description: string;
  start_date: string;
  end_date: string;
  duration: string;
  duration_days: number;
  owner: string;
  status: string;
  dependency_predecessor: string;
  milestone: boolean;
  notes: string;
  date_assumption: boolean;
};

export type ProjectPlan = {
  file_id: string;
  project_title: string;
  generated_at: string;
  assumptions: string[];
  missing_information: string[];
  tasks: PlanTask[];
};

export type OutputFile = {
  name: string;
  path: string;
  size_bytes: number;
  download_url: string;
};

export type BillingConfig = {
  payment_required: boolean;
  tap_configured: boolean;
  amount: number;
  currency: string;
  interval: string;
  interval_days: number;
  save_card_requested: boolean;
};

export type BillingSubscription = {
  email: string;
  status: string;
  plan: string;
  amount: number;
  currency: string;
  current_period_end?: string;
  tap_charge_id?: string;
  tap_customer_id?: string;
  tap_card_id?: string;
  tap_payment_agreement_id?: string;
};

export type BillingStatus = {
  active: boolean;
  email: string | null;
  subscription: BillingSubscription | null;
  payment_required: boolean;
};

export type CheckoutPayload = {
  email: string;
  first_name: string;
  last_name: string;
  phone_country_code: string;
  phone_number?: string;
};

export type CheckoutResponse = {
  checkout_url: string;
  tap_charge_id?: string;
  amount: number;
  currency: string;
  save_card_requested: boolean;
};

export type ProjectSnapshot = {
  metadata: ProjectMetadata;
  analysis: Analysis | null;
  plan: ProjectPlan | null;
  has_text_cache: boolean;
};
