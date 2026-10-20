---
name: quiniela-rentable
description: Use ONLY when analyzing Spanish Quiniela jornada 14, boleto multiples reducidas, LAE percentages, triples dobles Super 13. Construye apuesta rentable 18€ o segura.
---

# Quiniela Rentable - Jornada LAE

Metodo validado en jornada 14 26/27 para decidir entre bote y asegurar.

## 1. Leer boleto real (no captura)
- `m-signo` en `button.u-pronostico` = marcado. Sin `m-signo` = no marcado.
- Contar: dobles = 2 marcas, triples = 3 marcas.
- Sistema objetivo: reduccion 3a oficial `3 dobles + 3 triples = 24 apuestas = 18€ Super 13`.
- Directo serian `2^3*3^3=216 apuestas=162€`. Reducida garantiza 13 si base entra, 14 con 24/216=11.1%.

## 2. Datos a cruzar por partido 1-14 + pleno 15
- Del boleto: `% Jugados / % LAE / % Probables` por 1X2.
- Del repo: `data/db/quiniela.json` -> `modelo {1,X,2}`, `valor = modelo-LAE`, `value_pick`.
- Clasificacion actual: LaLiga (Barca, Atleti, Betis, Madrid... colistas Malaga, Elche, Valencia), Segunda (Eibar 21, Castellon 20, Mallorca 17, Sabadell 16, Burgos 14, Las Palmas 11), Liga F (Barca, Madrid CFF 13, Madrid 13, Athletic 11, Eibar 11, Valencia 0).
- Forma: ultimos 5, casa/fuera, Europa League jueves (desgaste 3 dias vs 9), bajas (Vini 4 partidos, Nico/Sancet, Pepe/Buchanan, Angel expulsado), H2H FBref/Flashscore.
- Pleno 15 goles 0/1/2/M: seguro `1-1` (53%x52% LAE, 36%x36% prob), loco bote `2-0` (7%+45% jugado) o `2-1` (7%+35% jugado). Pleno no afecta 13/14.

## 3. Reglas de marca
- Triple solo en X alta probables 29-33%: tipos `4 Valencia-Ath 29-28-43, 8 Eibar-Mallorca 37-29-34, 10 Burgos-Sabadell 36-31-33`.
- Doble valor = `1-2`, no `1X`, salvo Celta-like donde X>2: `1:34.5-22.2-43.4 =>1-2`, `2:53.9-20.2-25.9 valor 2 +18.9 =>1-2`, `6:31.6-24.8-43.6 valor 1 +11.6 + Real Europa =>1-2`, `9:25.5-24.1-50.4 valor 2 +12.4 =>X-2`, `5:47.1-27-25.9 =>1X`.
- Fijo solo si modelo >60% o LAE >75% sin valor en contra: `7 Madrid-Sevilla 64.4% =>1`, `11 Athletic F-Valencia F 73.5% vs 0pts =>1`.
- Trampas a romper siempre: `12 Madrid F-Espanyol F 44.4-21.3-34.3 vs 83-10-7 LAE 96% jugado valor 2 +27.3 => triple o 1-2`, `14 Atleti F-Madrid CFF 45-20.9-34.2 Madrid CFF 2a vs Atleti 8a valor 2 +11.2 + H2H 3V-5E-0 Atleti`.
- `7` nunca se dobla para ahorrar.

## 4. Dos boletos segun objetivo
**Bote 2M (rentable):** triples `4,10,12` + dobles `1:1-2,2:1-2,9:X-2`, fijos `3:2,5:1,6:2,7:1,11:1,13:1,14:2`, pleno `1-1` AL15, o loco `2-0/2-1` gratis al 15.

**Asegurar 12-14 (probabilidad):** triples `4,8,10` + dobles `1:X2,5:1X,9:X2`, fijos `2:1,3:2,6:2,7:1,11:1,12:1,13:1,14:1`, pleno `1-1`. Premio esperado ~6.000€, olvida bote.

## 5. Respuesta
- Corta, directa, sin validar por validar. Corregir si `14:1` cuando Madrid CFF es 2a, o `12:1` al 96%.
- Si captura borrosa, pedir HTML: `m-signo` manda.
- Explicar garantia: 24/216, Super13/12/11.
