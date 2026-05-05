"use client";

import { Coffee, Sun, MoonStar, Sunset, Coffee as Cafe } from "lucide-react";

const ALL_REFEICOES = [
  { key: "cafe_manha", label: "Café da Manhã", icon: Cafe },
  { key: "almoco", label: "Almoço", icon: Sun },
  { key: "lanche_tarde", label: "Lanche da Tarde", icon: Sunset },
  { key: "jantar", label: "Jantar", icon: MoonStar },
  { key: "lanche_manha", label: "Lanche da Manhã", icon: Coffee },
  { key: "ceia", label: "Ceia", icon: MoonStar },
];

export function MealSelector({ selected, onChange }: { selected: string[]; onChange: (meals: string[]) => void }) {
  function toggle(key: string) {
    if (selected.includes(key)) {
      onChange(selected.filter((k) => k !== key));
    } else {
      onChange([...selected, key]);
    }
  }

  return (
    <div className="space-y-2">
      <label className="block text-xs font-medium text-ink-muted-80">Refeições</label>
      <div className="grid grid-cols-2 gap-2">
        {ALL_REFEICOES.map((ref) => {
          const Icon = ref.icon;
          const active = selected.includes(ref.key);
          return (
            <button
              key={ref.key}
              type="button"
              onClick={() => toggle(ref.key)}
              className={`flex items-center gap-2 rounded-md border px-3 py-2 text-left text-sm font-medium transition-all ${
                active
                  ? "border-ink bg-primary-subtle text-ink"
                  : "border-hairline bg-white text-ink-muted-48 hover:bg-surface-soft"
              }`}
            >
              <Icon size={14} />
              <span className="truncate">{ref.label}</span>
              {active && <span className="ml-auto text-xs font-medium text-ink">✓</span>}
            </button>
          );
        })}
      </div>
      {selected.length === 0 && (
        <p className="text-xs text-amber-600">Selecione pelo menos uma refeição</p>
      )}
    </div>
  );
}
