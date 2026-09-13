import "dotenv/config";

function required(name: string): string {
  const value = process.env[name];
  if (!value && process.env.NODE_ENV === "production") {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value ?? "";
}

function optional(name: string, fallback: string): string {
  return process.env[name] || fallback;
}

export const env = {
  appId: required("APP_ID"),
  appSecret: required("APP_SECRET"),
  isProduction: process.env.NODE_ENV === "production",
  databaseUrl: required("DATABASE_URL"),
  geminiApiKey: process.env.GEMINI_API_KEY || "",
  valoAlpha: parseFloat(optional("VALO_ALPHA", "1.0")),
  valoC0: parseFloat(optional("VALO_C0", "1.0")),
  slackSigningSecret: process.env.SLACK_SIGNING_SECRET || "",
};
