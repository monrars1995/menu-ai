"use client";

import { useEffect, useMemo, useState } from "react";
import { Bot, CheckCircle2, RefreshCcw, Save, Send } from "lucide-react";
import { useApi } from "@/lib/api";

type SlotType = "contract_analyzer" | "generator" | "reviewer" | "copilot";

interface AdminLlmModel {
  id: string;
  label?: string;
  provider?: string;
  description?: string;
  enabled?: boolean;
  supports_generation?: boolean;
  supports_review?: boolean;
}

interface AgentVersion {
  id: string;
  profile_id: string;
  version_number: number;
  status: "draft" | "published" | "archived";
  provider_model_id: string;
  system_prompt: string;
  allowed_tools: string[];
  enabled: boolean;
  publish_notes?: string;
  published_at?: string;
}

interface AgentProfile {
  id: string;
  name: string;
  slug: string;
  description?: string;
  slot_type: SlotType;
  enabled: boolean;
  draft_version?: AgentVersion | null;
  active_published_version?: AgentVersion | null;
  published_versions: AgentVersion[];
}

interface Binding {
  id: string;
  flow_key: string;
  slot_type: SlotType;
  enabled: boolean;
  profile_id?: string | null;
  version_id?: string | null;
  profile_name?: string | null;
  version_number?: number | null;
}

interface AgentsMetaPayload {
  flow_key: string;
  slot_types: SlotType[];
  tool_names: string[];
}

interface CreateAgentForm {
  name: string;
  slug: string;
  description: string;
  slot_type: SlotType;
  provider_model_id: string;
  system_prompt: string;
  allowed_tools: string[];
  enabled: boolean;
  publish_notes: string;
}

interface ProfileForm {
  name: string;
  slug: string;
  description: string;
  enabled: boolean;
}

interface DraftForm {
  provider_model_id: string;
  system_prompt: string;
  allowed_tools: string[];
  enabled: boolean;
  publish_notes: string;
}

const SLOT_LABELS: Record<SlotType, string> = {
  contract_analyzer: "Analisador de contrato",
  generator: "Gerador",
  reviewer: "Revisor",
  copilot: "Copiloto operacional",
};

function slugify(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

function defaultCreateForm(models: AdminLlmModel[] = []): CreateAgentForm {
  const firstGeneratorModel = models.find((model) => model.supports_generation !== false)?.id || "openai-gpt-5.5";
  return {
    name: "",
    slug: "",
    description: "",
    slot_type: "generator",
    provider_model_id: firstGeneratorModel,
    system_prompt: "",
    allowed_tools: [],
    enabled: true,
    publish_notes: "",
  };
}

export default function AgentsPage() {
  const { apiFetch } = useApi();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [profiles, setProfiles] = useState<AgentProfile[]>([]);
  const [bindings, setBindings] = useState<Binding[]>([]);
  const [models, setModels] = useState<AdminLlmModel[]>([]);
  const [meta, setMeta] = useState<AgentsMetaPayload | null>(null);
  const [createForm, setCreateForm] = useState<CreateAgentForm>(defaultCreateForm());
  const [profileForms, setProfileForms] = useState<Record<string, ProfileForm>>({});
  const [draftForms, setDraftForms] = useState<Record<string, DraftForm>>({});
  const [bindingSelection, setBindingSelection] = useState<Record<string, string>>({});

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    const [profilesRes, bindingsRes, metaRes, modelsRes] = await Promise.all([
      apiFetch("/api/admin/agents/profiles"),
      apiFetch("/api/admin/agents/bindings"),
      apiFetch("/api/admin/agents/meta"),
      apiFetch("/api/admin/llm-models"),
    ]);
    if (!profilesRes.ok || !bindingsRes.ok || !metaRes.ok || !modelsRes.ok) {
      alert("Não foi possível carregar o painel de agentes.");
      setLoading(false);
      return;
    }
    const profilesPayload = await profilesRes.json();
    const bindingsPayload = await bindingsRes.json();
    const metaPayload = await metaRes.json();
    const modelsPayload = await modelsRes.json();
    const nextProfiles = Array.isArray(profilesPayload.items) ? (profilesPayload.items as AgentProfile[]) : [];
    const nextBindings = Array.isArray(bindingsPayload.items) ? (bindingsPayload.items as Binding[]) : [];
    const nextModels = Array.isArray(modelsPayload.models) ? (modelsPayload.models as AdminLlmModel[]) : [];
    setProfiles(nextProfiles);
    setBindings(nextBindings);
    setMeta(metaPayload as AgentsMetaPayload);
    setModels(nextModels);
    setCreateForm((prev) => ({
      ...defaultCreateForm(nextModels),
      ...prev,
      provider_model_id: prev.provider_model_id || defaultCreateForm(nextModels).provider_model_id,
    }));
    setProfileForms(
      Object.fromEntries(
        nextProfiles.map((profile) => [
          profile.id,
          {
            name: profile.name,
            slug: profile.slug,
            description: profile.description || "",
            enabled: profile.enabled,
          },
        ]),
      ),
    );
    setDraftForms(
      Object.fromEntries(
        nextProfiles.map((profile) => [
          profile.id,
          {
            provider_model_id:
              profile.draft_version?.provider_model_id ||
              profile.active_published_version?.provider_model_id ||
              defaultModelForSlot(profile.slot_type, nextModels),
            system_prompt:
              profile.draft_version?.system_prompt ||
              profile.active_published_version?.system_prompt ||
              "",
            allowed_tools:
              profile.draft_version?.allowed_tools ||
              profile.active_published_version?.allowed_tools ||
              [],
            enabled: profile.draft_version?.enabled ?? true,
            publish_notes: profile.draft_version?.publish_notes || "",
          },
        ]),
      ),
    );
    setBindingSelection(
      Object.fromEntries(nextBindings.map((binding) => [binding.slot_type, binding.profile_id || ""])),
    );
    setLoading(false);
  }

  const profilesBySlot = useMemo(() => {
    const grouped = new Map<SlotType, AgentProfile[]>();
    for (const profile of profiles) {
      const current = grouped.get(profile.slot_type) || [];
      current.push(profile);
      grouped.set(profile.slot_type, current);
    }
    return grouped;
  }, [profiles]);

  function defaultModelForSlot(slotType: SlotType, available: AdminLlmModel[]) {
    if (slotType === "reviewer") {
      return available.find((model) => model.supports_review)?.id || "queen-3.6";
    }
    return available.find((model) => model.supports_generation !== false)?.id || "openai-gpt-5.5";
  }

  function modelsForSlot(slotType: SlotType) {
    return models.filter((model) =>
      slotType === "reviewer" ? Boolean(model.supports_review) : model.supports_generation !== false,
    );
  }

  async function createAgent() {
    if (!createForm.name.trim() || !createForm.slug.trim() || !createForm.provider_model_id) {
      alert("Preencha nome, slug e modelo base do agente.");
      return;
    }
    setSaving("create");
    const res = await apiFetch("/api/admin/agents/profiles", {
      method: "POST",
      body: JSON.stringify(createForm),
    });
    setSaving(null);
    if (!res.ok) {
      alert(await res.text());
      return;
    }
    await load();
    setCreateForm(defaultCreateForm(models));
  }

  async function saveProfile(profileId: string) {
    setSaving(`profile:${profileId}`);
    const res = await apiFetch(`/api/admin/agents/profiles/${profileId}`, {
      method: "PATCH",
      body: JSON.stringify(profileForms[profileId]),
    });
    setSaving(null);
    if (!res.ok) {
      alert(await res.text());
      return;
    }
    await load();
  }

  async function saveDraft(profileId: string) {
    setSaving(`draft:${profileId}`);
    const res = await apiFetch(`/api/admin/agents/profiles/${profileId}/draft`, {
      method: "PATCH",
      body: JSON.stringify(draftForms[profileId]),
    });
    setSaving(null);
    if (!res.ok) {
      alert(await res.text());
      return;
    }
    await load();
  }

  async function publishProfile(profileId: string) {
    setSaving(`publish:${profileId}`);
    const res = await apiFetch(`/api/admin/agents/profiles/${profileId}/publish`, {
      method: "POST",
      body: JSON.stringify({ publish_notes: draftForms[profileId]?.publish_notes || "" }),
    });
    setSaving(null);
    if (!res.ok) {
      alert(await res.text());
      return;
    }
    await load();
  }

  async function saveBinding(slotType: SlotType) {
    const profileId = bindingSelection[slotType];
    if (!profileId) {
      alert("Selecione um agente publicado para este slot.");
      return;
    }
    setSaving(`binding:${slotType}`);
    const res = await apiFetch(`/api/admin/agents/bindings/${slotType}?flow_key=gerar`, {
      method: "PUT",
      body: JSON.stringify({ profile_id: profileId, enabled: true }),
    });
    setSaving(null);
    if (!res.ok) {
      alert(await res.text());
      return;
    }
    await load();
  }

  if (loading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-hairline)] border-t-[var(--color-ink)]" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-page-title">Agents</h1>
          <p className="text-subtitle">
            Governança dos agentes publicados que alimentam os slots do fluxo de geração.
          </p>
        </div>
        <button className="btn-secondary" type="button" onClick={load}>
          <RefreshCcw size={14} className="mr-1.5 inline" />
          Atualizar
        </button>
      </div>

      <section className="surface p-5">
        <div className="mb-4 flex items-center gap-2">
          <Bot size={16} />
          <h2 className="text-base font-medium text-[var(--text-primary)]">Bindings ativos do fluxo /gerar</h2>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {(meta?.slot_types || []).map((slotType) => {
            const currentBinding = bindings.find((binding) => binding.slot_type === slotType);
            const slotProfiles = (profilesBySlot.get(slotType) || []).filter((profile) => profile.active_published_version);
            return (
              <div key={slotType} className="rounded-lg border border-[var(--color-hairline)] p-4">
                <div className="mb-2">
                  <p className="text-sm font-medium text-[var(--text-primary)]">{SLOT_LABELS[slotType]}</p>
                  <p className="text-xs text-[var(--text-tertiary)]">
                    Ativo: {currentBinding?.profile_name || "Sem agente publicado"}
                    {currentBinding?.version_number ? ` · v${currentBinding.version_number}` : ""}
                  </p>
                </div>
                <select
                  value={bindingSelection[slotType] || ""}
                  onChange={(event) =>
                    setBindingSelection((prev) => ({ ...prev, [slotType]: event.target.value }))
                  }
                  className="mb-3 h-10 w-full rounded-md border border-[var(--color-hairline)] bg-white px-3 text-sm"
                >
                  <option value="">Selecione um agente publicado</option>
                  {slotProfiles.map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {profile.name} · {profile.active_published_version?.provider_model_id}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn-primary text-sm"
                  disabled={saving === `binding:${slotType}`}
                  onClick={() => saveBinding(slotType)}
                >
                  <CheckCircle2 size={14} className="mr-1.5 inline" />
                  {saving === `binding:${slotType}` ? "Salvando..." : "Aplicar binding"}
                </button>
              </div>
            );
          })}
        </div>
      </section>

      <section className="surface p-5">
        <h2 className="mb-4 text-base font-medium text-[var(--text-primary)]">Criar novo agente</h2>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <Input
            label="Nome"
            value={createForm.name}
            onChange={(value) =>
              setCreateForm((prev) => ({
                ...prev,
                name: value,
                slug: prev.slug || slugify(value),
              }))
            }
          />
          <Input label="Slug" value={createForm.slug} onChange={(value) => setCreateForm((prev) => ({ ...prev, slug: slugify(value) }))} />
          <SelectField
            label="Slot"
            value={createForm.slot_type}
            options={(meta?.slot_types || []).map((slot) => ({ value: slot, label: SLOT_LABELS[slot] }))}
            onChange={(value) =>
              setCreateForm((prev) => ({
                ...prev,
                slot_type: value as SlotType,
                provider_model_id: defaultModelForSlot(value as SlotType, models),
              }))
            }
          />
          <SelectField
            label="Modelo base"
            value={createForm.provider_model_id}
            options={modelsForSlot(createForm.slot_type).map((model) => ({
              value: model.id,
              label: `${model.label || model.id} · ${model.id}`,
            }))}
            onChange={(value) => setCreateForm((prev) => ({ ...prev, provider_model_id: value }))}
          />
        </div>
        <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1fr)_22rem]">
          <TextArea
            label="System prompt"
            rows={6}
            value={createForm.system_prompt}
            onChange={(value) => setCreateForm((prev) => ({ ...prev, system_prompt: value }))}
          />
          <div className="space-y-3">
            <TextArea
              label="Descrição"
              rows={4}
              value={createForm.description}
              onChange={(value) => setCreateForm((prev) => ({ ...prev, description: value }))}
            />
            <TextArea
              label="Notas de publicação"
              rows={2}
              value={createForm.publish_notes}
              onChange={(value) => setCreateForm((prev) => ({ ...prev, publish_notes: value }))}
            />
          </div>
        </div>
        <ToolPicker
          title="Tools permitidas"
          toolNames={meta?.tool_names || []}
          selected={createForm.allowed_tools}
          onToggle={(toolName) =>
            setCreateForm((prev) => ({
              ...prev,
              allowed_tools: prev.allowed_tools.includes(toolName)
                ? prev.allowed_tools.filter((item) => item !== toolName)
                : [...prev.allowed_tools, toolName],
            }))
          }
        />
        <div className="mt-4 flex items-center justify-between gap-3">
          <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
            <input
              type="checkbox"
              checked={createForm.enabled}
              onChange={(event) => setCreateForm((prev) => ({ ...prev, enabled: event.target.checked }))}
            />
            Agente habilitado
          </label>
          <button type="button" className="btn-primary" onClick={createAgent} disabled={saving === "create"}>
            <Save size={14} className="mr-1.5 inline" />
            {saving === "create" ? "Criando..." : "Criar agente"}
          </button>
        </div>
      </section>

      {(meta?.slot_types || []).map((slotType) => (
        <section key={slotType} className="space-y-3">
          <div>
            <h2 className="text-base font-medium text-[var(--text-primary)]">{SLOT_LABELS[slotType]}</h2>
            <p className="text-xs text-[var(--text-tertiary)]">
              Draft editável + versões publicadas consumidas pelo runtime.
            </p>
          </div>
          {(profilesBySlot.get(slotType) || []).map((profile) => {
            const profileForm = profileForms[profile.id];
            const draftForm = draftForms[profile.id];
            if (!profileForm || !draftForm) return null;
            return (
              <article key={profile.id} className="surface p-5">
                <div className="mb-4 flex flex-wrap items-center gap-2">
                  <h3 className="text-base font-medium text-[var(--text-primary)]">{profile.name}</h3>
                  <span className="badge badge-default">{profile.slug}</span>
                  {profile.active_published_version && (
                    <span className="badge badge-primary">Publicado v{profile.active_published_version.version_number}</span>
                  )}
                  {!profile.enabled && <span className="badge badge-default">Desativado</span>}
                </div>

                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <Input
                    label="Nome"
                    value={profileForm.name}
                    onChange={(value) => setProfileForms((prev) => ({ ...prev, [profile.id]: { ...profileForm, name: value } }))}
                  />
                  <Input
                    label="Slug"
                    value={profileForm.slug}
                    onChange={(value) => setProfileForms((prev) => ({ ...prev, [profile.id]: { ...profileForm, slug: slugify(value) } }))}
                  />
                  <Input
                    label="Descrição"
                    value={profileForm.description}
                    onChange={(value) => setProfileForms((prev) => ({ ...prev, [profile.id]: { ...profileForm, description: value } }))}
                  />
                  <div className="flex items-end">
                    <label className="flex h-10 items-center gap-2 text-sm text-[var(--text-secondary)]">
                      <input
                        type="checkbox"
                        checked={profileForm.enabled}
                        onChange={(event) =>
                          setProfileForms((prev) => ({ ...prev, [profile.id]: { ...profileForm, enabled: event.target.checked } }))
                        }
                      />
                      Perfil habilitado
                    </label>
                  </div>
                </div>

                <div className="mt-3 flex justify-end">
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={saving === `profile:${profile.id}`}
                    onClick={() => saveProfile(profile.id)}
                  >
                    <Save size={14} className="mr-1.5 inline" />
                    {saving === `profile:${profile.id}` ? "Salvando..." : "Salvar perfil"}
                  </button>
                </div>

                <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
                  <div className="space-y-3">
                    <SelectField
                      label="Modelo do draft"
                      value={draftForm.provider_model_id}
                      options={modelsForSlot(profile.slot_type).map((model) => ({
                        value: model.id,
                        label: `${model.label || model.id} · ${model.id}`,
                      }))}
                      onChange={(value) =>
                        setDraftForms((prev) => ({ ...prev, [profile.id]: { ...draftForm, provider_model_id: value } }))
                      }
                    />
                    <TextArea
                      label="System prompt do draft"
                      rows={7}
                      value={draftForm.system_prompt}
                      onChange={(value) =>
                        setDraftForms((prev) => ({ ...prev, [profile.id]: { ...draftForm, system_prompt: value } }))
                      }
                    />
                    <ToolPicker
                      title="Tools permitidas no draft"
                      toolNames={meta?.tool_names || []}
                      selected={draftForm.allowed_tools}
                      onToggle={(toolName) =>
                        setDraftForms((prev) => ({
                          ...prev,
                          [profile.id]: {
                            ...draftForm,
                            allowed_tools: draftForm.allowed_tools.includes(toolName)
                              ? draftForm.allowed_tools.filter((item) => item !== toolName)
                              : [...draftForm.allowed_tools, toolName],
                          },
                        }))
                      }
                    />
                  </div>
                  <div className="space-y-3">
                    <TextArea
                      label="Notas de publicação"
                      rows={4}
                      value={draftForm.publish_notes}
                      onChange={(value) =>
                        setDraftForms((prev) => ({ ...prev, [profile.id]: { ...draftForm, publish_notes: value } }))
                      }
                    />
                    <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                      <input
                        type="checkbox"
                        checked={draftForm.enabled}
                        onChange={(event) =>
                          setDraftForms((prev) => ({ ...prev, [profile.id]: { ...draftForm, enabled: event.target.checked } }))
                        }
                      />
                      Draft habilitado para publicação
                    </label>
                    <div className="rounded-lg border border-[var(--color-hairline)] bg-[var(--surface-subtle)] p-3 text-xs text-[var(--text-secondary)]">
                      <p>Publicado ativo: {profile.active_published_version?.provider_model_id || "nenhum"}</p>
                      <p className="mt-1">Versões publicadas: {profile.published_versions.length}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="btn-secondary"
                        disabled={saving === `draft:${profile.id}`}
                        onClick={() => saveDraft(profile.id)}
                      >
                        <Save size={14} className="mr-1.5 inline" />
                        {saving === `draft:${profile.id}` ? "Salvando..." : "Salvar draft"}
                      </button>
                      <button
                        type="button"
                        className="btn-primary"
                        disabled={saving === `publish:${profile.id}`}
                        onClick={() => publishProfile(profile.id)}
                      >
                        <Send size={14} className="mr-1.5 inline" />
                        {saving === `publish:${profile.id}` ? "Publicando..." : "Publicar versão"}
                      </button>
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </section>
      ))}
    </div>
  );
}

function Input({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-xs font-medium text-[var(--text-tertiary)]">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full rounded-md border border-[var(--color-hairline)] bg-white px-3 text-sm"
      />
    </label>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-xs font-medium text-[var(--text-tertiary)]">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full rounded-md border border-[var(--color-hairline)] bg-white px-3 text-sm"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function TextArea({
  label,
  value,
  onChange,
  rows,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  rows: number;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-xs font-medium text-[var(--text-tertiary)]">{label}</span>
      <textarea
        rows={rows}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-md border border-[var(--color-hairline)] bg-white px-3 py-2 text-sm"
      />
    </label>
  );
}

function ToolPicker({
  title,
  toolNames,
  selected,
  onToggle,
}: {
  title: string;
  toolNames: string[];
  selected: string[];
  onToggle: (toolName: string) => void;
}) {
  return (
    <div className="mt-3">
      <p className="mb-2 text-xs font-medium text-[var(--text-tertiary)]">{title}</p>
      <div className="flex flex-wrap gap-2">
        {toolNames.map((toolName) => {
          const active = selected.includes(toolName);
          return (
            <button
              key={toolName}
              type="button"
              onClick={() => onToggle(toolName)}
              className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                active
                  ? "border-[var(--color-ink)] bg-[var(--surface-subtle)] text-[var(--color-ink)]"
                  : "border-[var(--color-hairline)] bg-white text-[var(--text-secondary)]"
              }`}
            >
              {toolName}
            </button>
          );
        })}
      </div>
    </div>
  );
}
