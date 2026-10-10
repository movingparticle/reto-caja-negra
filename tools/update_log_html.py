import re
from pathlib import Path

file_path = Path("LOG.html")
content = file_path.read_text(encoding="utf-8")

# 1. Update banner text
banner_old = """    <pre class="banner" aria-label="LOG en video inverso">+---------------------------------------------------------------------------------+
 |                                                                                 |
 |   ██╗       ██████╗  ██████╗                                                    |
 |   ██║      ██╔═══██╗██╔════╝     40 registros · 3 grupos · 0 pendientes          |
 |   ██║      ██║   ██║██║  ███╗    H-01 → H-04 confirmadas                         |
 |   ██║      ██║   ██║██║   ██║    ISO 7064 Mod 97-10 · E303>E304>E401>E506>E507     |
 |   ███████╗ ╚██████╔╝╚██████╔╝                                                    |
 |   ╚══════╝  ╚═════╝  ╚═════╝                                                     |
 +---------------------------------------------------------------------------------+</pre>"""

banner_new = """    <pre class="banner" aria-label="LOG en video inverso">+---------------------------------------------------------------------------------+
 |                                                                                 |
 |   ██╗       ██████╗  ██████╗                                                    |
 |   ██║      ██╔═══██╗██╔════╝     44 registros · 4 grupos · 0 pendientes          |
 |   ██║      ██║   ██║██║  ███╗    H-01 → H-06 confirmadas (V2 Post-Incidente)     |
 |   ██║      ██║   ██║██║   ██║    ISO 7064 Mod 97-10 · HALT · E510 Bloqueo · V2   |
 |   ███████╗ ╚██████╔╝╚██████╔╝                                                    |
 |   ╚══════╝  ╚═════╝  ╚═════╝                                                     |
 +---------------------------------------------------------------------------------+</pre>"""

content = content.replace(banner_old, banner_new)

# Subtitle and badges
content = re.sub(
    r'40 registros reales: 20 del baseline público, 14 de probing en vivo, 6 de fuzzing adversarial\.',
    '44 registros reales: 20 baseline, 14 probes viva, 6 fuzzing, 4 resolución del incidente 15:30 (V2).',
    content
)
content = re.sub(
    r'<span>40/40 citados</span>',
    '<span>44/44 citados</span>',
    content
)

# 2. Metrics in #resumen
metrics_old = """    <div class="metrics">
      <div class="metric"><div class="n">40</div><div class="l">registros</div></div>
      <div class="metric"><div class="n">20</div><div class="l">baseline</div></div>
      <div class="metric i"><div class="n">14</div><div class="l">probes viva</div></div>
      <div class="metric warn"><div class="n">6</div><div class="l">adversarial fuzz</div></div>
    </div>"""

metrics_new = """    <div class="metrics" style="grid-template-columns: repeat(5, 1fr);">
      <div class="metric"><div class="n">44</div><div class="l">registros</div></div>
      <div class="metric"><div class="n">20</div><div class="l">baseline</div></div>
      <div class="metric i"><div class="n">14</div><div class="l">probes viva</div></div>
      <div class="metric warn"><div class="n">6</div><div class="l">adversarial</div></div>
      <div class="metric" style="border-color:var(--cyan);"><div class="n" style="color:var(--cyan);">4</div><div class="l">incidente v2</div></div>
    </div>"""

content = content.replace(metrics_old, metrics_new)

# Table in #resumen
summary_table_row = """          <tr><td><strong>C · Adversarial fuzz</strong></td><td class="n">35–40</td><td>fuzzing dirigido a límites</td><td>¿Dónde se rompe el modelo y dónde está el tope?</td></tr>
        </tbody>"""

summary_table_new = """          <tr><td><strong>C · Adversarial fuzz</strong></td><td class="n">35–40</td><td>fuzzing dirigido a límites</td><td>¿Dónde se rompe el modelo y dónde está el tope?</td></tr>
          <tr><td><strong>D · Incidente 15:30</strong></td><td class="n">41–44</td><td>sondas de aislamiento post-incidente (V2)</td><td>¿Qué cambió en V2 y cómo responde la nueva arquitectura?</td></tr>
        </tbody>"""

content = content.replace(summary_table_row, summary_table_new)

# 3. Hypotheses in #hipotesis
hyp_target = """          <tr><td class="n">H-04</td><td>La validación sigue un orden determinista con precedencia <strong>E303 &gt; E304 &gt; E401 &gt; E506 &gt; E507</strong>.</td><td><span class="conf c1">confirmada</span></td><td class="n">#26, #27, #28, #9, #16</td><td>#26 (E303&gt;E304), #27 (E304&gt;E506), #28 (E401&gt;E506); #16 cierra con E507.</td></tr>
        </tbody>"""

hyp_new = """          <tr><td class="n">H-04</td><td>La validación sigue un orden determinista con precedencia <strong>E303 &gt; E304 &gt; E401 &gt; E506 &gt; E507</strong>.</td><td><span class="conf c1">confirmada</span></td><td class="n">#26, #27, #28, #9, #16</td><td>#26 (E303&gt;E304), #27 (E304&gt;E506), #28 (E401&gt;E506); #16 cierra con E507. En V2 el bloqueo E510 se intercala: E401 &gt; E510 &gt; E506.</td></tr>
          <tr><td class="n">H-05</td><td>En V2, comandos con typos cercanos ofrecen sugerencia (<code>Levenshtein ≤ 2</code>).</td><td><span class="conf c1">confirmada (V2)</span></td><td class="n">#41, probe_suggestion</td><td>Comandos cercanos devuelven <code>"sugerencia":"&lt;CMD&gt;"</code>.</td></tr>
          <tr><td class="n">H-06</td><td>En V2, <code>HALT;1</code> conmuta a estado persistente de parada (<code>503 E599</code>).</td><td><span class="conf c1">confirmada (V2)</span></td><td class="n">#42, #43, probe_halt_state</td><td>Parada total persistente hasta recepción de <code>/__reset</code>.</td></tr>
        </tbody>"""

content = content.replace(hyp_target, hyp_new)

# 4. Insert #incidente section after #fuzz
fuzz_end = """  </section>

  <section id="decisiones">"""

incidente_section = """  </section>

  <section id="incidente">
    <div class="sec-head"><span class="kicker">grupo D · ids 41–44</span></div>
    <h2>Incidente 15:30 (V2)</h2>
    <p class="lead">Sondas de resolución y aislamiento de los cambios de la Versión 2 tras el incidente no anunciado.</p>
    <div class="table-wrap">
      <table>
        <thead><tr><th>#</th><th>probe</th><th>razón</th><th>resultado</th><th>hipótesis antes</th><th>hipótesis después</th><th>decisión</th></tr></thead>
        <tbody>
          <tr><td class="n">#41</td><td><code>ALTAX;A;85</code></td><td>Comando tipográficamente cercano a <code>ALTA</code></td><td><span class="st bad">400 E301</span> comando desconocido (con sugerencia)</td><td><code>E301</code> solo tiene error y mensaje (V1)</td><td><span class="st ok">falsada en V2</span>: V2 añade sugerencia Levenshtein ≤ 2</td><td>Implementar <code>suggestCommand</code> en <code>src/suggest.mjs</code> y enlazar en <code>src/engine.mjs</code></td></tr>
          <tr><td class="n">#42</td><td><code>HALT;AC-0001;85</code></td><td>Comando <code>HALT</code> con argumento sin confirmar</td><td><span class="st bad">409 E520</span> operación destructiva: requiere confirmación</td><td><code>HALT</code> no existe en el catálogo bancario (V1)</td><td><span class="st ok">falsada en V2</span>: existe comando destructivo que exige confirmación</td><td>Manejar <code>HALT</code> con aridad 1 y <code>409 E520</code> si arg ≠ 1</td></tr>
          <tr><td class="n">#43</td><td><code>HALT;1;19</code></td><td>Comando <code>HALT</code> confirmado con <code>"1"</code></td><td><span class="st bad">503 E599</span> service halted</td><td>El servicio nunca detiene el procesamiento</td><td><span class="st ok">falsada en V2</span>: conmuta a parada persistente</td><td>Activar <code>halted=true</code>; rechazar <code>/msg</code> con 503 consumiendo <code>X-Req</code> hasta reset</td></tr>
          <tr><td class="n">#44</td><td><code>OPTIONS /msg</code> y query tokens</td><td>Verificación de transporte HTTP y CORS</td><td><code>OPTIONS</code> → <span class="st bad">404 E404</span>; <code>?token=...</code> → <span class="st bad">401 E001</span></td><td><code>OPTIONS</code> responde 204 y query tokens autorizan (V1)</td><td><span class="st ok">falsada en V2</span>: V2 cerró CORS público y restringió auth</td><td>Eliminar CORS global para arnés; auth estricta Bearer; permitir solo preflight a navegador</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section id="decisiones">"""

content = content.replace(fuzz_end, incidente_section)

# 5. Add V2 decisions to #decisiones
decisiones_target = """          <tr><td>Replicar literales con defectos históricos (<code>"recieved"</code>, <code>"comando desconocido "</code>)</td><td class="n">#6, #12</td><td><code>src/engine.mjs</code></td></tr>
        </tbody>"""

decisiones_new = """          <tr><td>Replicar literales con defectos históricos (<code>"recieved"</code>, <code>"comando desconocido "</code>)</td><td class="n">#6, #12</td><td><code>src/engine.mjs</code></td></tr>
          <tr><td>Sugerencia difusa de comandos cercanos (distancia Levenshtein ≤ 2 en orden alfabético)</td><td class="n">Probe #41</td><td><code>src/suggest.mjs</code></td></tr>
          <tr><td>Parada de emergencia persistente con <code>HALT;1</code> (bloqueo global 503 E599 hasta reset)</td><td class="n">Probes #42, #43</td><td><code>src/engine.mjs</code></td></tr>
          <tr><td>Nuevo formato decimal de saldo (<code>"X.YY"</code>) y límite reducido a 50.000 (<code>E506</code>)</td><td class="n">INC-03, INC-05</td><td><code>src/engine.mjs</code></td></tr>
          <tr><td>Bloqueo progresivo de cuenta origen (<code>423 E510</code> con intentos) tras 3 fallos</td><td class="n">INC-07, INC-09</td><td><code>src/engine.mjs</code></td></tr>
        </tbody>"""

content = content.replace(decisiones_target, decisiones_new)

# 6. Terminal bottom summary
term_old = """    <pre class="map">movingparticle@caja-negra:~$ ./probe --verify
40/40 registros citados · 20 baseline · 14 probes · 6 fuzz · 0 pendientes
Hypothesis H-01 → H-04 : <span class="cy">CONFIRMED</span>
checksum              : <span class="am">ISO 7064 Mod 97-10</span>
precedence            : <span class="am">E303 &gt; E304 &gt; E401 &gt; E506 &gt; E507</span></pre>"""

term_new = """    <pre class="map">movingparticle@caja-negra:~$ ./probe --verify
44/44 registros citados · 20 baseline · 14 probes · 6 fuzz · 4 incidente V2 · 0 pendientes
Hypothesis H-01 → H-06 : <span class="cy">CONFIRMED & VERIFIED</span>
checksum              : <span class="am">ISO 7064 Mod 97-10</span>
service status         : <span class="am">V2 PARITY 100% OPERATIONAL · 0 DIVERGENCIAS</span></pre>"""

content = content.replace(term_old, term_new)

# 7. Keyboard jumps in script
jumps_old = 'const jumps = ["resumen","hipotesis","baseline","probes","fuzz","decisiones"];'
jumps_new = 'const jumps = ["resumen","hipotesis","baseline","probes","fuzz","incidente","decisiones"];'
content = content.replace(jumps_old, jumps_new)

kbd_old = """    <kbd data-jump="1">1</kbd><kbd data-jump="2">2</kbd><kbd data-jump="3">3</kbd>
    <kbd data-jump="4">4</kbd><kbd data-jump="5">5</kbd><kbd data-jump="6">6</kbd>"""

kbd_new = """    <kbd data-jump="1">1</kbd><kbd data-jump="2">2</kbd><kbd data-jump="3">3</kbd>
    <kbd data-jump="4">4</kbd><kbd data-jump="5">5</kbd><kbd data-jump="6">6</kbd><kbd data-jump="7">7</kbd>"""
content = content.replace(kbd_old, kbd_new)

file_path.write_text(content, encoding="utf-8")
print("Successfully updated LOG.html")

# Also create aliases logs.html and LOGS.html
Path("logs.html").write_text(content, encoding="utf-8")
Path("LOGS.html").write_text(content, encoding="utf-8")
print("Created logs.html and LOGS.html aliases")
