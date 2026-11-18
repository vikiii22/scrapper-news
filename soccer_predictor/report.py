"""Informe de la jornada en Markdown y JSON."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _pct(value: Optional[Dict[str, Any]], keys=("1", "X", "2")) -> str:
    if not value:
        return "n/d"
    parts = []
    for key in keys:
        raw = value.get(key)
        if raw is None:
            return "n/d"
        parts.append(f"{float(raw):.0f}")
    return "/".join(parts)


def _signs_for(signs: Dict[Any, Any], n: int) -> List[str]:
    return list(signs.get(n) or signs.get(str(n)) or [])


def _pick_label(match: Dict[str, Any]) -> str:
    pick = match.get("pick") or "-"
    value_pick = match.get("value_pick")
    return f"{pick} (valor {value_pick})" if value_pick else str(pick)


def _value_label(match: Dict[str, Any]) -> str:
    values = match.get("valor") or {}
    if not values:
        return "n/d"
    sign = max(values, key=lambda key: values[key])
    return f"{sign} {float(values[sign]):+.1f}"


def _form_label(match: Dict[str, Any]) -> str:
    context = match.get("context") or {}
    form = context.get("form") or {}
    home = (form.get("home") or {}).get("recent")
    away = (form.get("away") or {}).get("recent")
    if not home and not away:
        return "n/d"
    return f"{home or 'n/d'} / {away or 'n/d'}"


def _xg_label(match: Dict[str, Any]) -> str:
    context = match.get("context") or {}
    form = context.get("form") or {}
    home = form.get("home") or {}
    away = form.get("away") or {}
    if home.get("xg") is None and away.get("xg") is None:
        return "n/d"
    return f"{home.get('xg', 'n/d')} / {away.get('xg', 'n/d')}"


def _elo_label(match: Dict[str, Any]) -> str:
    context = match.get("context") or {}
    elo = context.get("elo") or {}
    home, away = elo.get("home"), elo.get("away")
    if home is None and away is None:
        return "n/d"
    return f"{home if home is not None else 'n/d'} / {away if away is not None else 'n/d'}"


def _absences_label(match: Dict[str, Any]) -> str:
    absences = match.get("absences") or {}
    if not absences:
        context = match.get("context") or {}
        injuries = context.get("injuries") or {}
        home = (injuries.get("home") or {}).get("count")
        away = (injuries.get("away") or {}).get("count")
    else:
        home, away = absences.get("home"), absences.get("away")
    return f"{home if home is not None else 'n/d'} / {away if away is not None else 'n/d'}"


def _botoes(entry: Dict[str, Any]) -> str:
    lines: List[str] = []
    for key in ("boleto_rentable", "boleto_conservador"):
        boleto = entry.get(key)
        if not boleto:
            continue
        title = boleto.get("name") or ("Boleto rentable" if "rentable" in key else "Boleto conservador")
        lines.append(f"## {title}")
        lines.append("")
        lines.append(f"**{boleto.get('bets', 24)} apuestas · {boleto.get('cost_eur', 18.0):.2f} €**")
        lines.append("")
        multiples = boleto.get("multiples") or {}
        lines.append(
            f"Triples: {', '.join(str(n) for n in multiples.get('triples', [])) or '-'} · "
            f"Dobles: {', '.join(str(n) for n in multiples.get('dobles', [])) or '-'}"
        )
        lines.append("")
        lines.append("| # | Partido | Signos |")
        lines.append("|---:|---|---|")
        signs = boleto.get("signs") or {}
        for n in sorted((int(k) for k in signs), key=int):
            match = next((m for m in entry.get("matches", []) if int(m.get("n", 0)) == n), {})
            name = f"{match.get('home', '?')} - {match.get('away', '?')}"
            lines.append(f"| {n} | {name} | {' '.join(_signs_for(signs, n))} |")
        lines.append("")
        lines.append("```")
        for column in boleto.get("columns") or []:
            lines.append(" ".join(column))
        lines.append("```")
        lines.append("")
        pleno = boleto.get("pleno") or {}
        lines.append(f"**Pleno:** {pleno.get('home', '1')}-{pleno.get('away', '1')}")
        guarantee = boleto.get("guarantee") or {}
        lines.append(
            f"**Garantía:** {guarantee.get('text', 'n/d')} "
            f"(14 al {guarantee.get('p14', 11.1):.1f} %)"
        )
        lines.append("")
    return "\n".join(lines)


def render_markdown(entry: Dict[str, Any]) -> str:
    matches: List[Dict[str, Any]] = list(entry.get("matches") or [])
    lines: List[str] = []
    lines.append(f"# JORNADA {entry.get('jornada', '?')} — {entry.get('close', 'cierre n/d')}")
    lines.append("")
    lines.append(f"Generado: {entry.get('fetched_at') or datetime.now().isoformat(timespec='seconds')}")
    lines.append("")

    sources = entry.get("sources") or {}
    if sources:
        lines.append("## Fuentes")
        lines.append("")
        lines.append("| Fuente | Estado | Nota |")
        lines.append("|---|---|---|")
        for name, source in sources.items():
            if isinstance(source, dict):
                status = "OK" if source.get("ok") else "n/d"
                note = source.get("note") or source.get("error") or ""
            else:
                status = "OK" if source else "n/d"
                note = ""
            lines.append(f"| {name} | {status} | {note} |")
        lines.append("")

    lines.append("## Partidos")
    lines.append("")
    lines.append("| # | Local | Visitante | Hora | %Jug | %LAE | %Prob | Modelo 1X2 | Valor | Forma | xG | Elo | Bajas | Pick |")
    lines.append("|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for match in matches:
        percentages = match.get("percentages") or {}
        lines.append(
            "| {n} | {home} | {away} | {hour} | {jug} | {lae} | {prob} | {model} | {value} | "
            "{form} | {xg} | {elo} | {abs} | {pick} |".format(
                n=match.get("n", ""),
                home=match.get("home", "?"),
                away=match.get("away", "?"),
                hour=match.get("hour") or "n/d",
                jug=_pct(percentages.get("jugados")),
                lae=_pct(percentages.get("lae")),
                prob=_pct(percentages.get("probables")),
                model=_pct(match.get("modelo")),
                value=_value_label(match),
                form=_form_label(match),
                xg=_xg_label(match),
                elo=_elo_label(match),
                abs=_absences_label(match),
                pick=_pick_label(match),
            )
        )
    lines.append("")

    lines.append("## Lectura")
    lines.append("")
    for match in matches:
        if match.get("n") == 15:
            continue
        context = match.get("context") or {}
        injuries = context.get("injuries") or {}
        home_out = (injuries.get("home") or {}).get("count", "n/d")
        away_out = (injuries.get("away") or {}).get("count", "n/d")
        note = "baja confianza" if match.get("low_confidence") else "confianza normal"
        lines.append(
            f"- **{match.get('n')}. {match.get('home')} - {match.get('away')}**: "
            f"pick {match.get('pick', 'n/d')}, valor {_value_label(match)}, "
            f"bajas {home_out}/{away_out}, {note}."
        )
    lines.append("")

    lines.append("## Pleno al 15")
    lines.append("")
    pleno_match = next((m for m in matches if m.get("n") == 15), None)
    if pleno_match:
        pleno = pleno_match.get("pleno") or {}
        home = pleno.get("home") or {}
        away = pleno.get("away") or {}
        lines.append(f"**{pleno_match.get('home')} - {pleno_match.get('away')}**")
        lines.append("")
        lines.append("| Equipo | 0 | 1 | 2 | M |")
        lines.append("|---|---|---|---|---|")
        lines.append(
            f"| {pleno_match.get('home')} | {home.get('0', 'n/d')} | "
            f"{home.get('1', 'n/d')} | {home.get('2', 'n/d')} | {home.get('M', 'n/d')} |"
        )
        lines.append(
            f"| {pleno_match.get('away')} | {away.get('0', 'n/d')} | "
            f"{away.get('1', 'n/d')} | {away.get('2', 'n/d')} | {away.get('M', 'n/d')} |"
        )
        lines.append("")
        suggested = pleno_match.get("pleno_sugerido") or (entry.get("boleto_rentable") or {}).get("pleno") or {}
        lines.append(f"Recomendación segura: **{suggested.get('home', 'n/d')}-{suggested.get('away', 'n/d')}**")
        variants = entry.get("pleno_variants") or {}
        if variants.get("bota"):
            lines.append(
                f"Alternativa bote: **{variants['bota'].get('home')}-{variants['bota'].get('away')}**"
            )
    else:
        lines.append("n/d")
    lines.append("")

    lines.append(_botoes(entry))

    lines.append("## Riesgos")
    lines.append("")
    risks = [
        m for m in matches
        if m.get("low_confidence")
        or any(value is None for value in (m.get("percentages") or {}).values())
        or not (m.get("context") or {}).get("form")
    ]
    if risks:
        for match in risks:
            lines.append(
                f"- Partido {match.get('n')} ({match.get('home')} - {match.get('away')}): "
                "datos incompletos o baja confianza; contraste manual recomendado."
            )
    else:
        lines.append("- Sin riesgos destacados.")
    lines.append("")

    lines.append("---")
    lines.append(
        "Herramienta estadística: las predicciones son probabilidades, no certezas. "
        "No es consejo de apuestas."
    )
    return "\n".join(lines)


def write_report(entry: Dict[str, Any], output_dir: Path = Path("output")) -> tuple[Path, Path]:
    matches = entry.get("matches") or []
    if len(matches) != 15:
        raise ValueError(f"el informe requiere 15 partidos, hay {len(matches)}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    day = datetime.now().date().isoformat()
    base = f"jornada_{entry.get('jornada', 'x')}_{day}"
    markdown_path = output_dir / f"{base}.md"
    json_path = output_dir / f"{base}.json"

    markdown_path.write_text(render_markdown(entry), encoding="utf-8")
    json_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    return markdown_path, json_path
