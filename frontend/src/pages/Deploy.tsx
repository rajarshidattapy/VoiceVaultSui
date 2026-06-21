import { useState, useEffect } from "react";
import { Helmet } from "react-helmet-async";
import { Navbar } from "@/components/layout/Navbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Loader2, Rocket, Mic2, BrainCircuit, DollarSign,
  Play, Pause, Trash2, Copy, CheckCircle2, ExternalLink,
  PhoneCall, Headphones, GraduationCap, UserCircle2, Settings2, Zap,
} from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { useSuiWallet } from "@/hooks/useSuiWallet";
import { useVoiceMetadata } from "@/hooks/useVoiceMetadata";
import { agentApi, AgentConfig } from "@/lib/agentApi";

// ── Templates ────────────────────────────────────────────────────────────────

const TEMPLATES = [
  {
    id: "sales",
    name: "Sales Agent",
    emoji: "💼",
    description: "Outbound sales calls using your voice",
    prompt: "You are an elite sales agent. Your goal is to engage prospects warmly, understand their needs, and present compelling value propositions. Be concise, confident, and always guide the conversation toward a positive outcome.",
  },
  {
    id: "support",
    name: "Support Agent",
    emoji: "🎧",
    description: "Inbound support, FAQs & booking",
    prompt: "You are a friendly customer support agent. Help users resolve their issues quickly and efficiently. Always be patient, empathetic, and solutions-focused.",
  },
  {
    id: "tutor",
    name: "Tutor Agent",
    emoji: "🎓",
    description: "Educational voice tutor",
    prompt: "You are an expert tutor. Break down complex topics into simple explanations. Ask clarifying questions, give examples, and adapt your teaching style to the learner's level.",
  },
  {
    id: "creator",
    name: "Creator Clone",
    emoji: "🎤",
    description: "Fans talk to your AI self",
    prompt: "You are a digital version of the creator. Respond in their authentic style — engaging, personal, and true to their brand. Share their perspectives and create meaningful interactions.",
  },
  {
    id: "custom",
    name: "Custom Agent",
    emoji: "⚙️",
    description: "Write your own system prompt",
    prompt: "",
  },
];

const LLM_PROVIDERS = [
  { value: "gpt-4o",            label: "OpenAI GPT-4o" },
  { value: "claude-3-5-sonnet", label: "Claude 3.5 Sonnet" },
  { value: "gemini-1.5-pro",    label: "Gemini 1.5 Pro" },
  { value: "groq-llama-3",      label: "Groq Llama 3" },
];

// ── Stepper ──────────────────────────────────────────────────────────────────

const STEPS = ["Voice", "Template", "Configure", "Deploy"];

function Stepper({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-2 mb-10">
      {STEPS.map((label, i) => {
        const n = i + 1;
        const done = current > n;
        const active = current === n;
        return (
          <div key={n} className="flex items-center gap-2">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
              active  ? "bg-primary text-primary-foreground shadow" :
              done    ? "bg-primary/20 text-primary" :
                        "bg-muted text-muted-foreground"
            }`}>
              <span className={`flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold ${
                active ? "bg-white/20" : done ? "bg-primary/30" : "bg-muted-foreground/20"
              }`}>{done ? "✓" : n}</span>
              <span className="hidden sm:inline">{label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`h-px w-6 ${done ? "bg-primary" : "bg-border"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function StatusBadge({ status }: { status: AgentConfig["status"] }) {
  if (status === "live")   return <Badge className="bg-green-600 hover:bg-green-600 text-xs">● Live</Badge>;
  if (status === "paused") return <Badge variant="secondary" className="text-xs">⏸ Paused</Badge>;
  return <Badge variant="outline" className="text-xs">○ Idle</Badge>;
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function Deploy() {
  const { address, isConnected } = useSuiWallet();
  const { metadata: ownVoice, isLoading: loadingVoice } = useVoiceMetadata(address || null);

  const [step, setStep] = useState(1);
  const [templateId, setTemplateId] = useState("");
  const [agentName, setAgentName] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [llmProvider, setLlmProvider] = useState("gpt-4o");
  const [pricePerCall, setPricePerCall] = useState("0.1");
  const [x402Enabled, setX402Enabled] = useState(true);
  const [x402Price, setX402Price] = useState("0.1");
  const [x402Uses, setX402Uses] = useState("2");
  const [deploying, setDeploying] = useState(false);
  const [deployResult, setDeployResult] = useState<null | {
    joinUrl: string; roomName: string; startCmd: string; liveKitConfigured: boolean;
  }>(null);
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!address) return;
    setLoadingAgents(true);
    agentApi.list(address).then(setAgents).finally(() => setLoadingAgents(false));
  }, [address]);

  const selectTemplate = (t: typeof TEMPLATES[0]) => {
    setTemplateId(t.id);
    if (!agentName) setAgentName(t.name);
    if (t.prompt) setSystemPrompt(t.prompt);
    setStep(3);
  };

  const handleDeploy = async () => {
    if (!address || !ownVoice) return;
    setDeploying(true);
    try {
      const { agent } = await agentApi.create(address, {
        agent_name:     agentName,
        template_id:    templateId,
        system_prompt:  systemPrompt,
        llm_provider:   llmProvider,
        price_per_call:    parseFloat(pricePerCall) || 0.1,
        voice_name:        ownVoice.name,
        voice_uri:         ownVoice.modelUri,
        voice_id:          ownVoice.voiceId,
        x402_enabled:      x402Enabled,
        x402_price_sui:    parseFloat(x402Price) || 0.1,
        x402_uses:         parseInt(x402Uses) || 2,
      } as any);

      const result = await agentApi.deploy(agent.id);
      setDeployResult(result);
      setAgents(prev => [{ ...agent, status: "live" as const }, ...prev]);
      toast.success("Agent deployed!", { description: agent.agent_name });
    } catch (err: any) {
      toast.error("Deployment failed", { description: err.message });
    } finally {
      setDeploying(false);
    }
  };

  const handlePauseToggle = async (id: string, currentStatus: string) => {
    const next = currentStatus === "live" ? "paused" : "live";
    await (next === "paused" ? agentApi.pause(id) : agentApi.resume(id));
    setAgents(prev => prev.map(a => a.id === id ? { ...a, status: next as any } : a));
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this agent? This cannot be undone.")) return;
    await agentApi.delete(id);
    setAgents(prev => prev.filter(a => a.id !== id));
    toast.success("Agent deleted");
  };

  const handleJoin = async (agentId: string) => {
    try {
      const result = await agentApi.talk(agentId, address || "user");
      if (result.joinUrl) {
        window.open(result.joinUrl, "_blank");
      } else {
        toast.info("Set LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET in .env to enable live voice.", {
          duration: 8000,
        });
      }
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const copyText = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ── Not connected ──────────────────────────────────────────────────────────

  if (!isConnected) {
    return (
      <>
        <Helmet><title>Deploy Agent - VoiceVault</title></Helmet>
        <div className="min-h-screen bg-background">
          <Navbar />
          <main className="pt-40 flex justify-center px-4">
            <Card className="max-w-md w-full text-center p-8">
              <Rocket className="h-12 w-12 mx-auto mb-4 text-primary" />
              <CardTitle className="mb-2">Connect Your Wallet</CardTitle>
              <CardDescription>Connect your Sui wallet to deploy voice agents</CardDescription>
            </Card>
          </main>
        </div>
      </>
    );
  }

  // ── Main ──────────────────────────────────────────────────────────────────

  return (
    <>
      <Helmet><title>Deploy Agent - VoiceVault</title></Helmet>
      <div className="min-h-screen bg-background">
        <Navbar />
        <main className="pt-32 pb-20">
          <div className="container max-w-2xl mx-auto px-4">

            <div className="mb-8">
              <h1 className="font-display text-4xl font-bold mb-2">
                Deploy Your <span className="gradient-text">Voice Agent</span>
              </h1>
              <p className="text-muted-foreground text-sm">
                Own Your Voice. Deploy Your Agent. Earn Forever.
              </p>
            </div>

            <Stepper current={step} />

            {/* ── Step 1: Voice ─────────────────────────────────────────────── */}
            {step === 1 && (
              <Card>
                <CardHeader>
                  <CardTitle>Select Your Voice</CardTitle>
                  <CardDescription>Your registered on-chain voice becomes the agent's voice</CardDescription>
                </CardHeader>
                <CardContent>
                  {loadingVoice ? (
                    <div className="flex items-center gap-2 text-muted-foreground py-8 justify-center">
                      <Loader2 className="h-5 w-5 animate-spin" /> Checking blockchain...
                    </div>
                  ) : ownVoice ? (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between p-4 rounded-xl border bg-primary/5">
                        <div>
                          <p className="font-semibold">{ownVoice.name}</p>
                          <p className="text-xs text-muted-foreground mt-0.5">{ownVoice.rights} · {ownVoice.pricePerUse} SUI/use</p>
                        </div>
                        <Badge className="bg-green-600 hover:bg-green-600">Verified ✓</Badge>
                      </div>
                      <Button className="w-full" onClick={() => setStep(2)}>
                        Use This Voice →
                      </Button>
                    </div>
                  ) : (
                    <Alert>
                      <AlertDescription className="space-y-3">
                        <p className="font-medium">No registered voice found.</p>
                        <p className="text-sm text-muted-foreground">
                          Register your voice on-chain first, then come back to deploy your agent.
                        </p>
                        <Button variant="outline" size="sm" onClick={() => window.location.href = "/upload"}>
                          Register Voice →
                        </Button>
                      </AlertDescription>
                    </Alert>
                  )}
                </CardContent>
              </Card>
            )}

            {/* ── Step 2: Template ──────────────────────────────────────────── */}
            {step === 2 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold text-lg">Pick a Template</h2>
                  <Button variant="ghost" size="sm" onClick={() => setStep(1)}>← Back</Button>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {TEMPLATES.map(t => (
                    <button
                      key={t.id}
                      onClick={() => selectTemplate(t)}
                      className="text-left p-4 border rounded-xl transition-all hover:border-primary hover:bg-primary/5 active:scale-[0.98]"
                    >
                      <div className="text-2xl mb-2">{t.emoji}</div>
                      <p className="font-semibold text-sm">{t.name}</p>
                      <p className="text-xs text-muted-foreground mt-1">{t.description}</p>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* ── Step 3: Configure ─────────────────────────────────────────── */}
            {step === 3 && (
              <Card>
                <CardHeader>
                  <CardTitle>Configure Agent</CardTitle>
                  <CardDescription>
                    {TEMPLATES.find(t => t.id === templateId)?.emoji}{" "}
                    {TEMPLATES.find(t => t.id === templateId)?.name}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="space-y-2">
                    <Label>Agent Name</Label>
                    <Input
                      value={agentName}
                      onChange={e => setAgentName(e.target.value)}
                      placeholder="e.g. Alex Support Bot"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>System Prompt</Label>
                    <Textarea
                      value={systemPrompt}
                      onChange={e => setSystemPrompt(e.target.value)}
                      placeholder="Describe how your agent should behave..."
                      className="min-h-[110px]"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>LLM Provider</Label>
                      <Select value={llmProvider} onValueChange={setLlmProvider}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {LLM_PROVIDERS.map(p => (
                            <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label>Price per Call (SUI)</Label>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        value={pricePerCall}
                        onChange={e => setPricePerCall(e.target.value)}
                        placeholder="0.10"
                      />
                    </div>
                  </div>

                  {/* x402 Pay-Per-Use Settings */}
                  <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Zap className="h-4 w-4 text-primary" />
                        <span className="text-sm font-medium">x402 Pay-Per-Use Access</span>
                      </div>
                      <Switch checked={x402Enabled} onCheckedChange={setX402Enabled} />
                    </div>
                    {x402Enabled && (
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label className="text-xs text-muted-foreground">Price per session (SUI)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            min="0.01"
                            value={x402Price}
                            onChange={e => setX402Price(e.target.value)}
                            placeholder="0.10"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-xs text-muted-foreground">Uses per payment</Label>
                          <Input
                            type="number"
                            step="1"
                            min="1"
                            value={x402Uses}
                            onChange={e => setX402Uses(e.target.value)}
                            placeholder="2"
                          />
                        </div>
                      </div>
                    )}
                    <p className="text-xs text-muted-foreground">
                      {x402Enabled
                        ? `Callers pay ${x402Price} SUI for ${x402Uses} uses — no full license needed.`
                        : "Full license required for access. Enable to allow casual callers."}
                    </p>
                  </div>

                  <div className="flex gap-3 pt-2">
                    <Button variant="outline" onClick={() => setStep(2)} className="flex-1">← Back</Button>
                    <Button
                      onClick={() => setStep(4)}
                      disabled={!agentName.trim() || !systemPrompt.trim()}
                      className="flex-1"
                    >
                      Review & Deploy →
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* ── Step 4: Deploy ──────────────────────────────────────────��─── */}
            {step === 4 && (
              <div className="space-y-4">
                {!deployResult ? (
                  <Card>
                    <CardHeader>
                      <CardTitle>Review & Deploy</CardTitle>
                      <CardDescription>Confirm your agent configuration</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-5">
                      <div className="rounded-xl border bg-muted/30 divide-y">
                        {[
                          ["Voice",    ownVoice?.name || "—"],
                          ["Template", TEMPLATES.find(t => t.id === templateId)?.name || "—"],
                          ["Agent",    agentName],
                          ["LLM",      LLM_PROVIDERS.find(p => p.value === llmProvider)?.label || llmProvider],
                          ["Price",    `${pricePerCall} SUI / call`],
                          ["x402",     x402Enabled ? `${x402Price} SUI / ${x402Uses} uses` : "Disabled"],
                        ].map(([k, v]) => (
                          <div key={k} className="flex justify-between items-center px-4 py-2.5 text-sm">
                            <span className="text-muted-foreground">{k}</span>
                            <span className="font-medium">{v}</span>
                          </div>
                        ))}
                      </div>

                      <div className="flex gap-3">
                        <Button variant="outline" onClick={() => setStep(3)} className="flex-1">← Back</Button>
                        <Button onClick={handleDeploy} disabled={deploying} className="flex-1" size="lg">
                          {deploying
                            ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Deploying...</>
                            : <><Rocket className="mr-2 h-4 w-4" />Deploy Agent</>}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <Card className="border-green-500/40 bg-green-500/5">
                    <CardContent className="pt-6 space-y-5">
                      <div className="flex items-center gap-3">
                        <CheckCircle2 className="h-8 w-8 text-green-500 shrink-0" />
                        <div>
                          <p className="font-semibold text-green-600 dark:text-green-400">Agent Live!</p>
                          <p className="text-sm text-muted-foreground">Room: <code>{deployResult.roomName}</code></p>
                        </div>
                      </div>

                      {deployResult.joinUrl ? (
                        <Button className="w-full" onClick={() => window.open(deployResult.joinUrl, "_blank")}>
                          <ExternalLink className="mr-2 h-4 w-4" /> Open Voice Room
                        </Button>
                      ) : (
                        <Alert>
                          <AlertDescription className="text-sm space-y-2">
                            <p className="font-medium">LiveKit not configured — voice room disabled.</p>
                            <p className="text-muted-foreground">
                              Add <code className="bg-muted px-1 rounded text-xs">LIVEKIT_URL</code>,{" "}
                              <code className="bg-muted px-1 rounded text-xs">LIVEKIT_API_KEY</code>,{" "}
                              <code className="bg-muted px-1 rounded text-xs">LIVEKIT_API_SECRET</code> to your{" "}
                              <code className="bg-muted px-1 rounded text-xs">.env</code>.
                            </p>
                          </AlertDescription>
                        </Alert>
                      )}

                      <div className="space-y-1.5">
                        <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
                          Start agent worker
                        </p>
                        <div className="flex items-start gap-2 bg-muted rounded-lg p-3">
                          <code className="text-xs flex-1 break-all leading-relaxed">{deployResult.startCmd}</code>
                          <Button size="icon" variant="ghost" className="h-6 w-6 shrink-0" onClick={() => copyText(deployResult.startCmd)}>
                            {copied ? <CheckCircle2 className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
                          </Button>
                        </div>
                      </div>

                      <Button variant="outline" className="w-full" onClick={() => {
                        setStep(1); setDeployResult(null);
                        setAgentName(""); setTemplateId(""); setSystemPrompt("");
                      }}>
                        + Deploy Another Agent
                      </Button>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}

            {/* ── Your Agents ───────────────────────────────────────────────── */}
            <div className="mt-16">
              <h2 className="text-xl font-semibold mb-5">Your Agents</h2>

              {loadingAgents ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : agents.length === 0 ? (
                <div className="text-center py-12 border-2 border-dashed rounded-xl">
                  <Rocket className="h-10 w-10 mx-auto mb-3 text-muted-foreground/30" />
                  <p className="text-muted-foreground text-sm">No agents deployed yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {agents.map(agent => (
                    <Card key={agent.id}>
                      <CardContent className="py-4 px-5">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-semibold truncate">{agent.agent_name}</span>
                              <StatusBadge status={agent.status} />
                              <Badge variant="outline" className="text-xs">{agent.llm_provider}</Badge>
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">
                              🎤 {agent.voice_name || "—"} · {agent.price_per_call} SUI/call
                            </p>
                            <p className="text-xs text-muted-foreground">
                              📞 {agent.calls_count} calls · 💰 {agent.total_earned_sui.toFixed(3)} SUI
                            </p>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <Button size="sm" onClick={() => handleJoin(agent.id)} disabled={agent.status === "paused"}>
                              <Play className="h-3.5 w-3.5 mr-1" /> Talk
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => handlePauseToggle(agent.id, agent.status)}>
                              {agent.status === "live"
                                ? <><Pause className="h-3.5 w-3.5 mr-1" />Pause</>
                                : <><Play className="h-3.5 w-3.5 mr-1" />Resume</>}
                            </Button>
                            <Button
                              size="sm" variant="ghost"
                              className="text-destructive hover:text-destructive"
                              onClick={() => handleDelete(agent.id)}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>

          </div>
        </main>
      </div>
    </>
  );
}
