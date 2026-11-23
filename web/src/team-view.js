import {icon,escapeHTML as esc} from './icons.js';

export function teamIntro(name,path,active){
  const modes=[['local','workspace','Este equipo','Entre tus ventanas e IDEs'],['lan','team','Red local','Entre estaciones de tu red'],['internet','globe','Internet','Entre redes distintas']];
  return `<div class="team-intro" ${active?'hidden':''}>
    <nav class="team-entry-tabs" role="tablist" aria-label="Conectar con CoCo">
      <button role="tab" aria-selected="true" aria-controls="coco-create-panel" id="coco-create-tab" data-team-entry="create">${icon('plus')}Crear sesión</button>
      <button role="tab" aria-selected="false" aria-controls="coco-join-panel" id="coco-join-tab" data-team-entry="join">${icon('arrow-right')}Unirme a una sesión</button>
    </nav>
    <div class="team-identity-row"><label>Tu nombre<input data-team-name maxlength="80" value="${esc(name)}" autocomplete="nickname"></label><p>${icon('shield')}Tú decides qué archivo compartir.</p></div>
    <div class="team-start">
      <section role="tabpanel" id="coco-create-panel" aria-labelledby="coco-create-tab" data-team-entry-panel="create">
        <div class="team-section-heading"><div><h4>Conecta tu espacio.</h4><p>El mismo archivo. Los cambios en tiempo real.</p></div><span class="team-file-chip">${icon('file')}${esc(path||'Abre un archivo de texto')}</span></div>
        <fieldset class="team-network-modes"><legend>¿Dónde está tu equipo?</legend>${modes.map(([value,glyph,title,note])=>`<label><input type="radio" name="coco-network" data-team-mode value="${value}" ${value==='local'?'checked':''}><span class="team-mode-icon">${icon(glyph)}</span><span class="team-mode-copy"><strong>${title}</strong><small>${note}</small></span><span class="team-mode-check">${icon('check')}</span></label>`).join('')}</fieldset>
        <p data-team-internet-info hidden>${icon('globe')}<span>Conexión HTTPS temporal con Cloudflare. El tráfico pasa por ese proveedor. La primera conexión descarga su conector verificado. Para desarrollo y pruebas, sin garantía de disponibilidad.</span></p>
        <label class="team-run-permission"><input type="checkbox" data-team-run><span><strong>Guardar y ejecutar en mi equipo</strong><small>Los participantes utilizarán las herramientas del anfitrión.</small></span></label>
        <div class="team-start-footer"><p>Comparte también los cambios sin guardar.<br>Puedes terminar la sesión en cualquier momento.</p><button class="primary-button" data-team-host>Crear sesión CoCo${icon('arrow-right')}</button></div>
      </section>
      <section role="tabpanel" id="coco-join-panel" aria-labelledby="coco-join-tab" data-team-entry-panel="join" hidden>
        <div class="team-join-mark">${icon('coco')}</div><h4>Tu equipo ya está dentro.</h4><p>Pega la invitación completa para entrar en su misma sesión de trabajo.</p>
        <label>Invitación<input data-team-invite placeholder="https://equipo/#invitación" aria-label="Invitación" autocomplete="off" spellcheck="false"></label>
        <div class="team-start-footer"><p>Zénit, VS Code o una IDE compatible.<br>El archivo se guarda en el equipo anfitrión.</p><button class="primary-button" data-team-join>Unirme${icon('arrow-right')}</button></div>
      </section>
    </div>
  </div>`;
}
