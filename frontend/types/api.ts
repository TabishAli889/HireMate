/** Mirrors `app/schemas/health.py` on the backend. */
export interface HealthResponse {
  status: "ok";
  app: string;
  version: string;
  environment: string;
  llm_configured: boolean;
  llm_model: string;
}
