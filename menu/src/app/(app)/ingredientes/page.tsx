"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import type { Ingrediente } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { PageHeader } from "@/components/layout/page-header";
import { Table, type Column } from "@/components/ui/table";
import { EmptyState } from "@/components/ui/empty-state";
import { InlineLoader } from "@/components/ui/loading";
import { Plus, Salad, Pencil, Trash2, Search } from "lucide-react";

export default function IngredientesPage() {
  const [ingredientes, setIngredientes] = useState<Ingrediente[]>([]);
  const [categorias, setCategorias] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [catFilter, setCatFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<Ingrediente | null>(null);
  const [deleting, setDeleting] = useState<Ingrediente | null>(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    nome: "", codigo: "", unidade_medida: "g", custo_unitario: "", categoria: "",
    fornecedor: "", calorias_100g: "", proteina_100g: "", carboidrato_100g: "", gordura_100g: "",
    fibra_100g: "", sodio_100g: "", alergeno: false, tipo_alergeno: "",
  });

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try {
      const [r, c] = await Promise.all([api.ingredientes.list(), api.ingredientes.categorias()]);
      setIngredientes(r.items || []);
      setCategorias(c.categorias || []);
    } catch {}
    setLoading(false);
  }

  function openCreate() {
    setForm({ nome: "", codigo: "", unidade_medida: "g", custo_unitario: "", categoria: "", fornecedor: "", calorias_100g: "", proteina_100g: "", carboidrato_100g: "", gordura_100g: "", fibra_100g: "", sodio_100g: "", alergeno: false, tipo_alergeno: "" });
    setEditing(null);
    setShowCreate(true);
  }

  function openEdit(i: Ingrediente) {
    setForm({
      nome: i.nome || "", codigo: i.codigo || "", unidade_medida: i.unidade_medida || "g",
      custo_unitario: i.custo_unitario?.toString() || "", categoria: i.categoria || "",
      fornecedor: i.fornecedor || "", calorias_100g: i.calorias_100g?.toString() || "",
      proteina_100g: i.proteina_100g?.toString() || "", carboidrato_100g: i.carboidrato_100g?.toString() || "",
      gordura_100g: i.gordura_100g?.toString() || "", fibra_100g: i.fibra_100g?.toString() || "",
      sodio_100g: i.sodio_100g?.toString() || "", alergeno: i.alergeno || false, tipo_alergeno: i.tipo_alergeno || "",
    });
    setEditing(i);
    setShowCreate(true);
  }

  async function handleSave() {
    setSaving(true);
    try {
      const data: any = {
        nome: form.nome, codigo: form.codigo || undefined, unidade_medida: form.unidade_medida,
        custo_unitario: form.custo_unitario ? parseFloat(form.custo_unitario) : 0,
        categoria: form.categoria || undefined, fornecedor: form.fornecedor || undefined,
        calorias_100g: form.calorias_100g ? parseFloat(form.calorias_100g) : undefined,
        proteina_100g: form.proteina_100g ? parseFloat(form.proteina_100g) : undefined,
        carboidrato_100g: form.carboidrato_100g ? parseFloat(form.carboidrato_100g) : undefined,
        gordura_100g: form.gordura_100g ? parseFloat(form.gordura_100g) : undefined,
        fibra_100g: form.fibra_100g ? parseFloat(form.fibra_100g) : undefined,
        sodio_100g: form.sodio_100g ? parseFloat(form.sodio_100g) : undefined,
        alergeno: form.alergeno, tipo_alergeno: form.tipo_alergeno || undefined,
      };
      if (editing) { await api.ingredientes.update(editing.id, data); } else { await api.ingredientes.create(data); }
      setShowCreate(false);
      await load();
    } catch (e: any) { alert(e.message || "Erro ao salvar"); }
    setSaving(false);
  }

  async function handleDelete() {
    if (!deleting) return;
    setSaving(true);
    try { await api.ingredientes.update(deleting.id, { ativo: false } as any); setDeleting(null); await load(); }
    catch (e: any) { alert(e.message || "Erro ao desativar"); }
    setSaving(false);
  }

  const filtered = ingredientes.filter((i) => {
    const matchSearch = i.nome.toLowerCase().includes(search.toLowerCase()) || (i.codigo || "").toLowerCase().includes(search.toLowerCase());
    const matchCat = !catFilter || i.categoria === catFilter;
    return matchSearch && matchCat;
  });

  const inputCls = "w-full rounded-md border border-hairline bg-white px-3 py-2 text-sm focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]";

  const columns: Column<Ingrediente>[] = [
    { key: "nome", header: "Nome", render: (i) => <span className="font-medium">{i.nome}</span> },
    { key: "categoria", header: "Categoria", render: (i) => i.categoria || "—" },
    { key: "unidade_medida", header: "Unidade" },
    { key: "custo_unitario", header: "Custo_unit.", render: (i) => formatCurrency(i.custo_unitario) },
    { key: "alergeno", header: "Alergeno", render: (i) => i.alergeno ? <span className="text-xs font-medium text-red-600">{i.tipo_alergeno || "Sim"}</span> : "—" },
    { key: "actions", header: "", className: "text-right", render: (i) => (
      <div className="flex items-center justify-end gap-1">
        <button onClick={() => openEdit(i)} className="rounded-md p-1 text-ink-muted-48 hover:bg-surface-soft hover:text-ink"><Pencil size={14} /></button>
        <button onClick={() => setDeleting(i)} className="rounded-md p-1 text-ink-muted-48 hover:bg-red-50 hover:text-red-600"><Trash2 size={14} /></button>
      </div>
    )},
  ];

  return (
    <div>
      <PageHeader title="Ingredientes" description="Catálogo de ingredientes e insumos" actions={<Button onClick={openCreate} size="sm"><Plus size={16} />Novo Ingrediente</Button>} />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted-48" />
          <input type="text" placeholder="Buscar…" value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-md border border-hairline bg-white py-2 pl-8 pr-3 text-sm placeholder:text-ink-muted-48 focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]" />
        </div>
        <select value={catFilter} onChange={(e) => setCatFilter(e.target.value)}
          className="rounded-md border border-hairline bg-white px-3 py-2 text-sm focus:border-info-border focus:outline-none focus:ring-2 focus:ring-[rgba(69,143,255,0.35)]">
          <option value="">Todas categorias</option>
          {categorias.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <div className="rounded-lg border border-hairline bg-white">
        {loading ? <div className="py-12 text-center"><InlineLoader text="Carregando…" /></div>
        : filtered.length === 0 ? <EmptyState icon={Salad} title="Nenhum ingrediente encontrado" actionLabel="Novo Ingrediente" onAction={openCreate} />
        : <Table columns={columns} data={filtered} keyExtractor={(i) => i.id} />}
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title={editing ? "Editar Ingrediente" : "Novo Ingrediente"} size="lg">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div><label className="mb-1 block text-xs font-medium text-ink-muted-80">Nome *</label><input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} required className={inputCls} /></div>
            <div><label className="mb-1 block text-xs font-medium text-ink-muted-80">Código</label><input value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} className={inputCls} /></div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div><label className="mb-1 block text-xs font-medium text-ink-muted-80">Categoria</label><input value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })} list="cat-list" className={inputCls} /><datalist id="cat-list">{categorias.map((c) => <option key={c} value={c} />)}</datalist></div>
            <div><label className="mb-1 block text-xs font-medium text-ink-muted-80">Unidade *</label><select value={form.unidade_medida} onChange={(e) => setForm({ ...form, unidade_medida: e.target.value })} className={inputCls}><option value="g">g</option><option value="kg">kg</option><option value="ml">ml</option><option value="l">l</option><option value="un">un</option></select></div>
            <div><label className="mb-1 block text-xs font-medium text-ink-muted-80">Custo (R$/un) *</label><input type="number" step="0.01" value={form.custo_unitario} onChange={(e) => setForm({ ...form, custo_unitario: e.target.value })} className={inputCls} /></div>
          </div>
          <div><label className="mb-1 block text-xs font-medium text-ink-muted-80">Fornecedor</label><input value={form.fornecedor} onChange={(e) => setForm({ ...form, fornecedor: e.target.value })} className={inputCls} /></div>
          <details className="group"><summary className="cursor-pointer text-xs font-medium text-ink-muted-48 hover:text-ink">Info. Nutricional (por 100g)</summary>
            <div className="mt-3 grid grid-cols-3 gap-3">
              <div><label className="mb-1 block text-[10px] font-medium text-ink-muted-48">Calorias</label><input type="number" step="0.1" value={form.calorias_100g} onChange={(e) => setForm({ ...form, calorias_100g: e.target.value })} className={inputCls} /></div>
              <div><label className="mb-1 block text-[10px] font-medium text-ink-muted-48">Proteína (g)</label><input type="number" step="0.1" value={form.proteina_100g} onChange={(e) => setForm({ ...form, proteina_100g: e.target.value })} className={inputCls} /></div>
              <div><label className="mb-1 block text-[10px] font-medium text-ink-muted-48">Carboidrato (g)</label><input type="number" step="0.1" value={form.carboidrato_100g} onChange={(e) => setForm({ ...form, carboidrato_100g: e.target.value })} className={inputCls} /></div>
              <div><label className="mb-1 block text-[10px] font-medium text-ink-muted-48">Gordura (g)</label><input type="number" step="0.1" value={form.gordura_100g} onChange={(e) => setForm({ ...form, gordura_100g: e.target.value })} className={inputCls} /></div>
              <div><label className="mb-1 block text-[10px] font-medium text-ink-muted-48">Fibra (g)</label><input type="number" step="0.1" value={form.fibra_100g} onChange={(e) => setForm({ ...form, fibra_100g: e.target.value })} className={inputCls} /></div>
              <div><label className="mb-1 block text-[10px] font-medium text-ink-muted-48">Sódio (mg)</label><input type="number" step="0.1" value={form.sodio_100g} onChange={(e) => setForm({ ...form, sodio_100g: e.target.value })} className={inputCls} /></div>
            </div>
          </details>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.alergeno} onChange={(e) => setForm({ ...form, alergeno: e.target.checked })} className="rounded" />Alergeno</label>
            {form.alergeno && <input value={form.tipo_alergeno} onChange={(e) => setForm({ ...form, tipo_alergeno: e.target.value })} placeholder="Tipo (ex: glúten)" className={inputCls.replace("w-full", "w-40")} />}
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" size="sm" onClick={() => setShowCreate(false)}>Cancelar</Button>
            <Button size="sm" onClick={handleSave} disabled={saving || !form.nome}>{saving ? "Salvando…" : "Salvar"}</Button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog open={!!deleting} onClose={() => setDeleting(null)} onConfirm={handleDelete}
        title="Desativar ingrediente" message={`Desativar "${deleting?.nome}"?`} confirmLabel="Desativar" danger loading={saving} />
    </div>
  );
}
