export interface User {
  id: string;
  nome?: string;
  email: string;
  role: string;
  empresa_id?: string;
}

export interface Empresa {
  id: string;
  nome: string;
  cnpj?: string;
  email?: string;
  telefone?: string;
  endereco?: string;
  logo_url?: string;
  segmento?: string;
  num_comensais?: number;
  ativo: boolean;
  created_at: string;
  updated_at: string;
}

export interface Contrato {
  id: string;
  empresa_id: string;
  nome: string;
  numero_contrato?: string;
  arquivo_path?: string;
  regras_json?: Record<string, unknown>;
  data_inicio?: string;
  data_fim?: string;
  custo_total_max?: number;
  custo_proteico_max?: number;
  num_refeicoes_dia?: number;
  estrutura_refeicao?: Record<string, number>;
  gramaturas_json?: Record<string, unknown>;
  incidencias_json?: Record<string, unknown>;
  proibicoes_json?: Record<string, unknown>;
  observacoes?: string;
  ativo: boolean;
  created_at: string;
  updated_at: string;
}

export interface Ingrediente {
  id: string;
  empresa_id?: string;
  codigo?: string;
  nome: string;
  nome_cientifico?: string;
  unidade_medida: string;
  custo_unitario: number;
  fornecedor?: string;
  fator_correcao?: number;
  calorias_100g?: number;
  proteina_100g?: number;
  carboidrato_100g?: number;
  gordura_100g?: number;
  fibra_100g?: number;
  sodio_100g?: number;
  alergeno?: boolean;
  tipo_alergeno?: string;
  meses_safra?: string[];
  categoria?: string;
  ativo: boolean;
  created_at: string;
  updated_at: string;
}

export interface FichaIngrediente {
  id?: string;
  ficha_tecnica_id?: string;
  ingrediente_id: string;
  quantidade_bruta_g: number;
  fator_correcao?: number;
  quantidade_liquida_g?: number;
  custo_calculado?: number;
  ordem?: number;
  observacao?: string;
  ingrediente_nome?: string;
}

export interface FichaTecnica {
  id: string;
  empresa_id: string;
  codigo?: string;
  nome: string;
  categoria?: string;
  rendimento_porcoes?: number;
  peso_porcao_g?: number;
  tempo_preparo_min?: number;
  modo_preparo?: string;
  equipamento?: string;
  dificuldade?: string;
  temperatura_servico?: string;
  custo_total?: number;
  custo_porcao?: number;
  calorias_porcao?: number;
  proteina_porcao?: number;
  carboidrato_porcao?: number;
  gordura_porcao?: number;
  sodio_porcao?: number;
  contem_gluten?: boolean;
  contem_lactose?: boolean;
  vegana?: boolean;
  vegetariana?: boolean;
  observacoes?: string;
  foto_url?: string;
  ativo: boolean;
  ingredientes?: FichaIngrediente[];
  created_at: string;
  updated_at: string;
}

export interface CardapioDia {
  id?: string;
  data?: string;
  numero_dia?: number;
  dia_semana?: string;
  custo_total?: number;
  observacoes?: string;
  refeicoes?: CardapioRefeicao[];
}

export interface CardapioRefeicao {
  id?: string;
  tipo_refeicao: string;
  ficha_tecnica_id?: string;
  codigo_prato?: string;
  nome_prato?: string;
  custo_porcao?: number;
  observacoes?: string;
  ordem?: number;
  ficha_tecnica_nome?: string;
}

export interface Cardapio {
  id: string;
  empresa_id: string;
  contrato_id?: string;
  criado_por_id?: string;
  nome: string;
  periodo_inicio?: string;
  periodo_fim?: string;
  status: string;
  custo_medio_dia?: number;
  num_dias?: number;
  resultado_raw?: Record<string, unknown>;
  parametros_json?: Record<string, unknown>;
  job_id?: string;
  observacoes?: string;
  dias?: CardapioDia[];
  created_at: string;
  updated_at: string;
}

export interface GerarRequest {
  empresa_id?: string;
  contrato_id?: string;
  dias: number;
  target_custo_total?: number;
  target_custo_proteico?: number;
  restricoes_usuario?: string;
  refeicoes?: string[];
  nome_cardapio?: string;
  llm_model?: string;
  contrato_analise_confirmada?: boolean;
}

export interface JobStatus {
  job_id: string;
  status: string;
  progresso: number;
  erro?: string;
  resultado?: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface LlmModel {
  id: string;
  label: string;
  provider?: string;
  model_string?: string;
  slug?: string;
  description?: string;
  enabled?: boolean;
}

export type Role = "super_admin" | "admin" | "nutricionista" | "gestor" | "visualizador";

export type CardapioStatus =
  | "rascunho"
  | "em_revisao"
  | "aguardando_aprovacao"
  | "aprovado"
  | "publicado"
  | "arquivado";

export type JobStatusEnum = "iniciando" | "executando" | "concluido" | "erro";

export type RefeicaoTipo = "cafe_manha" | "lanche_manha" | "almoco" | "lanche_tarde" | "jantar" | "ceia";

export interface ContratoAnalise {
  status: string;
  contrato_id?: string;
  nome_contrato?: string;
  numero_contrato?: string | null;
  mensagem?: string;
  necessidades: { observacoes?: string; estrutura_refeicao?: Record<string, unknown>; num_refeicoes_dia?: number };
  servicos: { num_refeicoes_dia?: number; estrutura?: Record<string, unknown> };
  gramaturas: Record<string, string>;
  incidencias: Record<string, string> | string[];
  proibicoes: string[];
  restricoes_alergenos: string[];
  dietas_especiais: string[];
  sazonalidade: string[] | boolean;
}

export interface GramaturaConferencia {
  total: number;
  conformes: number;
  nao_conformes: number;
  sem_dado: number;
  itens: { ficha: string; categoria: string; peso_ficha: number | null; gramatura_contrato: number | null; diferenca_g: number | null; diferenca_pct: number | null; status: string }[];
}
