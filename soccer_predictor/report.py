"""Informe de la jornada en Markdown y JSON."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _team(match: Dict[str, Any], side: str) -> str:
    name = match.get(side, "?")
    return f"{name} (F)" if match.get("is_women") else name


def _match_name(match: Dict[str, Any]) -> str:
    return f"{_team(match, 'home')} - {_team(match, 'away')}"


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


def _headline(match: Dict[str, Any]) -> str:
    news = (match.get("context") or {}).get("news") or {}
    items = news.get("items") if isinstance(news, dict) else None
    if not items and isinstance(news, dict):
        items = news.get("home") or []
    if items and isinstance(items[0], dict):
        return str(items[0].get("title") or "")
    return ""


def _absence_value(match: Dict[str, Any], side: str) -> Optional[int]:
    absences = match.get("absences")
    if isinstance(absences, dict) and absences.get(side) is not None:
        return absences.get(side)
    info = ((match.get("context") or {}).get("injuries") or {}).get(side) or {}
    return info.get("count") if info.get("ok") else None


def _absences_label(match: Dict[str, Any]) -> str:
    home = _absence_value(match, "home")
    away = _absence_value(match, "away")
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
            name = _match_name(match)
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
    if entry.get("forced") or entry.get("played"):
        lines.append(
            "> ⚠️ **JORNADA CERRADA — ANÁLISIS FORZADO**. "
            "Los boletos NO son jugables; el informe es solo para revisión."
        )
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
    lines.append("| # | Local | Visitante | Hora | %Jug | %LAE | %Prob | Modelo 1X2 | Valor | Forma C/F | xG5 C/F | Elo | Bajas | Pick |")
    lines.append("|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for match in matches:
        percentages = match.get("percentages") or {}
        lines.append(
            "| {n} | {home} | {away} | {hour} | {jug} | {lae} | {prob} | {model} | {value} | "
            "{form} | {xg} | {elo} | {abs} | {pick} |".format(
                n=match.get("n", ""),
                home=_team(match, "home"),
                away=_team(match, "away"),
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
    lines.append(
        "Si `%LAE` aún no está publicado, el `Valor` se calcula contra "
        "`%Probables` y se indica como `n/d` en la columna LAE."
    )
    lines.append("")

    lines.append("## Lectura")
    lines.append("")
    lines.append(
        "El `Pick` es el signo más probable del modelo. El boleto puede cubrirlo "
        "con doble o triple cuando el mercado no lo respalda (por ejemplo, un "
        "favorito local con mercado < 50 % y modelo > 8 puntos por encima)."
    )
    lines.append("")
    for match in matches:
        if match.get("n") == 15:
            continue
        home_out = _absence_value(match, "home")
        away_out = _absence_value(match, "away")
        note = "baja confianza" if match.get("low_confidence") else "confianza normal"
        headline = _headline(match)
        news_text = f", titular: «{headline}»" if headline else ""
        lines.append(
            f"- **{match.get('n')}. {_match_name(match)}**: "
            f"pick {match.get('pick', 'n/d')}, valor {_value_label(match)}, "
            f"bajas {'n/d' if home_out is None else home_out}/"
            f"{'n/d' if away_out is None else away_out}, {note}{news_text}. "
            f"Forma {_form_label(match)}; xG5 {_xg_label(match)}; "
            f"{match.get('competition', 'n/d')}."
        )
    lines.append("")

    lines.append("## Pleno al 15")
    lines.append("")
    pleno_match = next((m for m in matches if m.get("n") == 15), None)
    if pleno_match:
        pleno = pleno_match.get("pleno") or {}
        home = pleno.get("home") or {}
        away = pleno.get("away") or {}
        lines.append(f"**{_match_name(pleno_match)}**")
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
    risks = []
    for match in matches:
        if match.get("n") == 15:
            continue
        percentages = match.get("percentages") or {}
        missing = any(not percentages.get(key) for key in ("jugados", "probables"))
        if (match.get("low_confidence") or missing
                or not (match.get("context") or {}).get("form")):
            risks.append(match)
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
    day = (entry.get("fetched_at") or datetime.now().isoformat())[:10]
    base = f"jornada_{entry.get('jornada', 'x')}_{day}"
    markdown_path = output_dir / f"{base}.md"
    json_path = output_dir / f"{base}.json"

    markdown_path.write_text(render_markdown(entry), encoding="utf-8")
    json_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    return markdown_path, json_path
