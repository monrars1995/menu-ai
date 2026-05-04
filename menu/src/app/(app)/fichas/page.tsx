"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import type { FichaTecnica, FichaIngrediente, Ingrediente } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { PageHeader } from "@/components/layout/page-header";
import { Table, type Column } from "@/components/ui/table";
import { EmptyState } from "@/components/ui/empty-state";
import { InlineLoader } from "@/components/ui/loading";
import { Plus, BookOpen, Pencil, Trash2, Search, RefreshCw } from "lucide-react";

export default function FichasPage() {
  const [fichas, setFichas] = useState<FichaTecnica[]>([]);
  const [categorias, setCategorias] = useState<string[]>([]);
  const [ingredientes, setIngredientes] = useState<Ingrediente[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [catFilter, setCatFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<FichaTecnica | null>(null);
  const [deleting, setDeleting] = useState<FichaTecnica | null>(null);
  const [saving, setSaving] = useState(false);
  const [recalculating, setRecalculating] = useState<string | null>(null);

  const [form, setForm] = useState({
    nome: "", categoria: "", rendimento_porcoes: "", tempo_preparo_min: "",
    modo_preparo: "", observacoes: "", contem_gluten: false, contem_lactose: false, vegana: false, vegetariana: false,
    dificuldade: "",
  });
  const [ingrs, setIngrs] = useState<{ ingrediente_id: string; quantidade_bruta_g: string }[]>([]);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try {
      const [f, c, i] = await Promise.all([api.fichas.list(), api.fichas.categorias(), api.ingredientes.list()]);
      setFichas(f.items || []);
      setCategorias(c.categorias || []);
      setIngredientes(i.items || []);
    } catch {}
    setLoading(false);
  }

  function openCreate() {
    setForm({ nome: "", categoria: "", rendimento_porcoes: "", tempo_preparo_min: "", modo_preparo: "", observacoes: "", contem_gluten: false, contem_lactose: false, vegana: false, vegetariana: false, dificuldade: "" });
    setIngrs([]);
    setEditing(null);
    setShowCreate(true);
  }

  function openEdit(f: FichaTecnica) {
    setForm({
      nome: f.nome || "", categoria: f.categoria || "", rendimento_porcoes: f.rendimento_porcoes?.toString() || "",
      tempo_preparo_min: f.tempo_preparo_min?.toString() || "", modo_preparo: f.modo_preparo || "",
      observacoes: f.observacoes || "", contem_gluten: f.contem_gluten || false, contem_lactose: f.contem_lactose || false,
      vegana: f.vegana || false, vegetariana: f.vegetariana || false, dificuldade: f.dificuldade || "",
    });
    setIngrs((f.ingredientes || []).map((i) => ({ ingrediente_id: i.ingrediente_id, quantidade_bruta_g: i.quantidade_bruta_g?.toString() || "" })));
    setEditing(f);
    setShowCreate(true);
  }

  async function handleSave() {
    setSaving(true);
    try {
      const data: any = {
        nome: form.nome, categoria: form.categoria || undefined,
        rendimento_porcoes: form.rendimento_porcoes ? parseInt(form.rendimento_porcoes) : undefined,
        tempo_preparo_min: form.tempo_preparo_min ? parseInt(form.tempo_preparo_min) : undefined,
        modo_preparo: form.modo_preparo || undefined, observacoes: form.observacoes || undefined,
        contem_gluten: form.contem_gluten, contem_lactose: form.contem_lactose,
        vegana: form.vegana, vegetariana: form.vegetariana, dificuldade: form.dificuldade || undefined,
        ingredientes: ingrs.map((i) => ({ ingrediente_id: i.ingrediente_id, quantidade_bruta_g: parseFloat(i.quantidade_bruta_g) || 0 })),
      };
      if (editing) { await api.fichas.update(editing.id, data); } else { await api.fichas.create(data); }
      setShowCreate(false);
      await load();
    } catch (e: any) { alert(e.message || "Erro ao salvar"); }
    setSaving(false);
  }

  async function handleDelete() {
    if (!deleting) return;
    setSaving(true);
    try { await api.fichas.update(deleting.id, { ativo: false } as any); setDeleting(null); await load(); }
    catch (e: any) { alert(e.message || "Erro ao desativar"); }
    setSaving(false);
  }

  async function handleRecalcular(id: string) {
    setRecalculating(id);
    try { await api.fichas.recalcular(id); await load(); }
    catch (e: any) { alert(e.message || "Erro ao recalcular"); }
    setRecalculating(null);
  }

  const filtered = fichas.filter((f) => {
    const ms = f.nome.toLowerCase().includes(search.toLowerCase());
    const mc = !catFilter || f.categoria === catFilter;
    return ms && mc;
  });

  const inputCls = "w-full rounded-md border border-hairline bg-white px-3 py-2 text-sm focus:border-info-border focus:outline-none focus:ring-1 focus:ring-info-border";

  const columns: Column<FichaTecnica>[] = [
    { key: "nome", header: "Nome", render: (f) => <span className="font-medium">{f.nome}</span> },
    { key: "categoria", header: "Categoria", render: (f) => f.categoria || "—" },
    { key: "rendimento", header: "Porções", render: (f) => f.rendimento_porcoes || "—" },
    { key: "custo", header: "Custo Total", render: (f) => f.custo_total != null ? formatCurrency(f.custo_total) : "—" },
    { key: "tags", header: "Tags", render: (f) => (
      <div className="flex gap-1 flex-wrap">
        {f.contem_gluten && <span className="rounded-md border bg-amber-50 px-1.5 py-0.5 text-[9px] font-medium text-amber-700 border-amber-200">Glúten</span>}
        {f.contem_lactose && <span className="rounded-md border bg-blue-50 px-1.5 py-0.5 text-[9px] font-medium text-blue-700 border-blue-200">Lactose</span>}
        {f.vegana && <span className="rounded-md border bg-green-50 px-1.5 py-0.5 text-[9px] font-medium text-green-700 border-green-200">Vegana</span>}
      </div>
    )},
    { key: "actions", header: "", className: "text-right", render: (f) => (
      <div className="flex items-center justify-end gap-1">
        <button onClick={() => handleRecalcular(f.id)} disabled={recalculating === f.id} className="rounded-md p-1 text-ink-muted-48 hover:bg-surface-soft hover:text-ink" title="Recalcular"><RefreshCw size={14} className={recalculating === f.id ? "animate-spin" : ""} /></button>
        <button onClick={() => openEdit(f)} className="rounded-md p-1 text-ink-muted-48 hover:bg-surface-soft hover:text-ink"><Pencil size={14} /></button>
        <button onClick={() => setDeleting(f)} className="rounded-md p-1 text-ink-muted-48 hover:bg-red-50 hover:text-red-600"><Trash2 size={14} /></button>
      </div>
    )},
  ];

  return (
    <div>
      <PageHeader title="Fichas Técnicas" description="Receitas e fichas de preparo" actions={<Button onClick={openCreate} size="sm"><Plus size={16} />Nova Ficha</Button>} />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted-48" />
          <input type="text" placeholder="Buscar fichas…" value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-md border border-hairline bg-white py-2 pl-8 pr-3 text-sm placeholder:text-ink-muted-48 focus:border-info-border focus:outline-none focus:ring-1 focus:ring-info-border" />
        </div>
        <select value={catFilter} onChange={(e) => setCatFilter(e.target.value)}
          className="rounded-md border border-hairline bg-white px-3 py-2 text-sm focus:border-info-border focus:outline-none focus:ring-1 focus:ring-info-border">
          <option value="">Todas categorias</option>
          {categorias.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <div className="rounded-lg border border-hairline bg-white">
        {loading ? <div className="py-12 text-center"><InlineLoader text="Carregando…" /></div>
        : filtered.length === 0 ? <EmptyState icon={BookOpen} title="Nenhuma ficha encontrada" actionLabel="Nova Ficha" onAction={openCreate} />
        : <Table columns={columns} data={filtered} keyExtractor={(f) => f.id} />}
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title={editing ? "Editar Ficha" : "Nova Ficha"} size="lg">
        <div className="max-h-[70vh] space-y-4 overflow-y-auto pr-1">
          <div className="grid grid-cols-2 gap-4">
            <div><label className="mb-1 block text-xs font-medium text-ink-muted-80">Nome *</label><input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} required className={inputCls} /></div>
            <div><label className="mb-1 block text-xs font-medium text-ink-muted-80">Categoria</label><input value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })} list="cat-list-ficha" className={inputCls} /><datalist id="cat-list-ficha">{categorias.map((c) => <option key={c} value={c} />)}</datalist></div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div><label className="mb-1 block text-xs font-medium text-ink-muted-80">Porções</label><input type="number" value={form.rendimento_porcoes} onChange={(e) => setForm({ ...form, rendimento_porcoes: e.target.value })} className={inputCls} /></div>
            <div><label className="mb-1 block text-xs font-medium text-ink-muted-80">Tempo (min)</label><input type="number" value={form.tempo_preparo_min} onChange={(e) => setForm({ ...form, tempo_preparo_min: e.target.value })} className={inputCls} /></div>
            <div><label className="mb-1 block text-xs font-medium text-ink-muted-80">Dificuldade</label><select value={form.dificuldade} onChange={(e) => setForm({ ...form, dificuldade: e.target.value })} className={inputCls}><option value="">—</option><option value="facil">Fácil</option><option value="medio">Médio</option><option value="dificil">Difícil</option></select></div>
          </div>
          <div><label className="mb-1 block text-xs font-medium text-ink-muted-80">Modo de Preparo</label><textarea value={form.modo_preparo} onChange={(e) => setForm({ ...form, modo_preparo: e.target.value })} rows={3} className={inputCls} /></div>
          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.contem_gluten} onChange={(e) => setForm({ ...form, contem_gluten: e.target.checked })} className="rounded" />Contém Glúten</label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.contem_lactose} onChange={(e) => setForm({ ...form, contem_lactose: e.target.checked })} className="rounded" />Contém Lactose</label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.vegana} onChange={(e) => setForm({ ...form, vegana: e.target.checked })} className="rounded" />Vegana</label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.vegetariana} onChange={(e) => setForm({ ...form, vegetariana: e.target.checked })} className="rounded" />Vegetariana</label>
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-xs font-medium text-ink-muted-80">Ingredientes</label>
              <button onClick={() => setIngrs([...ingrs, { ingrediente_id: "", quantidade_bruta_g: "" }])} className="text-xs font-medium text-link hover:underline">+ Adicionar ingrediente</button>
            </div>
            {ingrs.length === 0 && <p className="text-xs text-ink-muted-48">Nenhum ingrediente adicionado</p>}
            <div className="space-y-2">
              {ingrs.map((ing, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <select value={ing.ingrediente_id} onChange={(e) => { const n = [...ingrs]; n[idx] = { ...n[idx], ingrediente_id: e.target.value }; setIngrs(n); }} className="flex-1 rounded-md border border-hairline bg-white px-2 py-1.5 text-sm">
                    <option value="">Selecione…</option>
                    {ingredientes.map((i) => <option key={i.id} value={i.id}>{i.nome}</option>)}
                  </select>
                  <input type="number" step="0.1" value={ing.quantidade_bruta_g} onChange={(e) => { const n = [...ingrs]; n[idx] = { ...n[idx], quantidade_bruta_g: e.target.value }; setIngrs(n); }} placeholder="g" className="w-20 rounded-md border border-hairline bg-white px-2 py-1.5 text-sm" />
                  <button onClick={() => setIngrs(ingrs.filter((_, i) => i !== idx))} className="text-ink-muted-48 hover:text-red-600">×</button>
                </div>
              ))}
            </div>
          </div>

          <div><label className="mb-1 block text-xs font-medium text-ink-muted-80">Observações</label><textarea value={form.observacoes} onChange={(e) => setForm({ ...form, observacoes: e.target.value })} rows={2} className={inputCls} /></div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" size="sm" onClick={() => setShowCreate(false)}>Cancelar</Button>
            <Button size="sm" onClick={handleSave} disabled={saving || !form.nome}>{saving ? "Salvando…" : "Salvar"}</Button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog open={!!deleting} onClose={() => setDeleting(null)} onConfirm={handleDelete}
        title="Desativar ficha" message={`Desativar "${deleting?.nome}"?`} confirmLabel="Desativar" danger loading={saving} />
    </div>
  );
}