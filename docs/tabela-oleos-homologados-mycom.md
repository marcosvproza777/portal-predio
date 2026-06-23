# Tabela de Óleos Homologados MAYEKAWA/MYCOM

## 1. Identificação

| Campo           | Valor                                              |
|----------------|----------------------------------------------------|
| Nome            | Tabela de Óleos Homologados MAYEKAWA/MYCOM         |
| Tipo            | Tabela técnica                                     |
| Fabricante      | MAYEKAWA / MYCOM                                   |
| Aplicação       | Compressores de refrigeração alternativos e parafuso MYCOM/MAYEKAWA |
| Arquivo         | `TABELAS DE ÓLEO HOMOLOGADOS (MAYEKAWA) (1).PDF`   |
| Páginas (ref.)  | 2 páginas                                          |
| Visibilidade    | Público para clientes autorizados                  |
| Status          | Ativo                                              |
| Uso pela IA     | Sim                                                |
| ID no mock      | `doc-mycom-002`                                    |

---

## 2. Óleos homologados cadastrados (ativos)

| Nome                         | Fabricante    | Fluido               | Classe       | cSt @40°C | Status      |
|------------------------------|---------------|----------------------|--------------|-----------|-------------|
| REFLO 68A                    | TECNO DATA    | NH3/R12/R22/R502     | PAO semi-sint| 58,0      | Homologado  |
| RAB 68                       | TEC SUMMIT    | NH3/R12/R22/R502     | PAO sintético| 56,0      | Homologado  |
| R 200                        | KLUBBER SUMMIT| NH3                  | PAO sintético| n/d       | Homologado  |
| MOBIL GARGOYLE ARCTIC SHC 226 E | MOBIL      | NH3/R12/R22/R502     | PAO sintético| 68,0      | Homologado  |
| MOBIL GARGOYLE ARCTIC EH     | MOBIL         | NH3/R12/R22/R502     | Mineral      | 68,0      | Homologado  |
| ESSO REFRIGERATION 68        | MOBIL/ESSO    | NH3/R12/R22/R502     | Mineral      | 68,0      | Homologado  |
| MOBIL EAL ARCTIC 68          | MOBIL         | R134a/R404a          | POE sintético| 68,0      | Homologado  |
| ICEMATIC SW 68               | CASTROL       | R134a/R404a          | POE sintético| 68,0      | Homologado  |
| CAPELLA HFC 68               | TEXACO        | R134a/R404a          | POE sintético| 68,0      | Homologado  |
| CAPELLA 68                   | TEXACO        | NH3/R12/R22          | Mineral      | 68,0      | Homologado  |
| **MYCOLD PAO**               | **MYCOM**     | **NH3/R22**          | **PAO sintético** | **53,0** | **Homologado** |

---

## 3. Regra MYCOLD AB 68

> **MYCOLD AB 68 foi descontinuado. No Portal Pred.IO, a referência atual deve ser MYCOLD PAO.**

| Campo            | Valor                          |
|-----------------|--------------------------------|
| Nome             | MYCOLD AB 68                   |
| Status           | Descontinuado                  |
| Substituído por  | MYCOLD PAO                     |
| Uso pela IA      | Apenas para redirecionamento   |
| Aparece para o cliente? | Nunca como ativo         |

### Regras de implementação:

- MYCOLD AB 68 **nunca aparece** na lista principal de óleos homologados do cliente.
- MYCOLD AB 68 **nunca é recomendado** pelo Assistente Técnico.
- MYCOLD AB 68 **nunca aparece** no plano de manutenção como óleo atual.
- MYCOLD AB 68 existe apenas como **alias histórico/inativo** para redirecionar a resposta ao MYCOLD PAO.
- Quando o cliente pergunta sobre MYCOLD AB 68, o assistente responde que foi descontinuado
  e que a referência atual é MYCOLD PAO.

---

## 4. Como o Assistente Técnico responde sobre óleo

### Pergunta sobre MYCOLD PAO
> O assistente responde com base na Tabela de Óleos Homologados MAYEKAWA/MYCOM e confirma
> que MYCOLD PAO é o óleo MYCOM homologado atual (ISO VG 68, PAO sintético, NH3/R22).

### Pergunta sobre MYCOLD AB 68
> O assistente responde que MYCOLD AB 68 foi descontinuado e deve ser substituído por MYCOLD PAO.
> Nunca recomenda MYCOLD AB 68 como óleo atual.

### Pergunta sobre lista de óleos homologados
> O assistente lista todos os 11 óleos ativos da tabela, informando fabricante, fluido e classe.
> Sempre orienta validação técnica antes da substituição.

### Pergunta sobre óleo para R134a/R404a
> O assistente informa as opções POE: MOBIL EAL ARCTIC 68, ICEMATIC SW 68, CAPELLA HFC 68.
> Sempre orienta validação técnica.

### Pergunta sobre óleo para Amônia/NH3
> O assistente informa as opções PAO e mineral compatíveis com NH3, incluindo MYCOLD PAO,
> REFLO 68A, RAB 68, R 200, MOBIL GARGOYLE ARCTIC SHC 226 E, GARGOYLE ARCTIC EH,
> ESSO REFRIGERATION 68 e CAPELLA 68.

### Pergunta "pode usar qualquer ISO 68?"
> O assistente responde que não. ISO VG 68 é apenas um dos critérios. A seleção depende
> do fluido refrigerante, classe do lubrificante, aplicação, condição operacional,
> compatibilidade e tabela homologada.

---

## 5. Como validar fluido refrigerante antes da recomendação

O assistente deve sempre considerar o fluido refrigerante da unidade antes de recomendar óleo:

| Fluido          | Classes compatíveis              |
|----------------|----------------------------------|
| NH3 (Amônia)   | PAO, mineral (não POE)           |
| R-22, R12, R502| PAO, mineral                     |
| R134a, R404a   | POE (não usar PAO ou mineral)    |

**Regra:** Nunca recomendar óleo sem conhecer o fluido refrigerante do equipamento.

---

## 6. Como exibir fonte

Toda resposta sobre óleo homologado deve citar:

```
Fonte: Tabela de Óleos Homologados MAYEKAWA/MYCOM
Botão: 📚 Abrir Tabela Técnica
```

---

## 7. Como impedir recomendação sem validação técnica

O assistente deve sempre incluir a seguinte orientação:
> "A aplicação deve ser validada conforme fluido, equipamento, condição operacional,
> análise de óleo e orientação técnica da equipe Pred.IO."

Nunca recomendar substituição de óleo sem validação técnica, pois:
- O fluido refrigerante determina a classe do lubrificante (POE/PAO/mineral).
- A condição do óleo atual (análise laboratorial) pode alterar o tipo recomendado.
- A compatibilidade com selos, borrachas e materiais internos deve ser verificada.

---

## 8. Segurança

- Documentos visíveis apenas para clientes autorizados (campo `Visibilidade`).
- MYCOLD AB 68 nunca aparece como óleo ativo para o cliente.
- Links dos PDFs são protegidos — nunca expostos diretamente sem autenticação.
- Nenhuma chave de storage ou IA exposta ao front-end.
- `client_id` sempre da sessão do servidor, nunca do front-end.
