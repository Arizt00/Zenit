// Classify only a direct first-person request, excluding quoted/code content.
// The concrete target is captured when the request starts.
export function requestsLiveEdit(question){
  const text=String(question).replace(/```[\s\S]*?(?:```|$)/g,'').replace(/^\s*>.*$/gm,'').replace(/["“][^"”]*["”]/g,'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  if(/\b(no|nunca|sin|don't|do not|never)\b/.test(text))return false;
  if(/\b(explica|explicame|analiza|analizame|opina|depura|revisa|explain|analy[sz]e|review|debug)\b/.test(text)&&!/(?:y|despues|luego|and|then)\s+(?:por favor\s+)?(?:escribe|reescribe|modifica|edita|cambia|crea|genera|write|rewrite|edit|change|create)/.test(text))return false;
  return /(?:^|[.!?]\s*|\b(?:por favor|puedes|quiero que|necesito que|please|can you|and|y)\s+)(?:escribe|escribir|reescribe|reescribir|modifica|modificar|edita|editar|cambia|cambiar|crea|crear|genera|generar|anade|anadir|implementa|implementar|write|rewrite|edit|change|create|generate|implement)\b/.test(text)&&/\b(en vivo|real[ -]?time|tiempo real|live|archivo|codigo|file|code)\b/.test(text);
}

// A direct request enables a reviewable companion session, never live editing.
export function requestsRealtimeHelp(question){
  const text=String(question).replace(/```[\s\S]*?(?:```|$)/g,'').replace(/^\s*>.*$/gm,'').replace(/["“][^"”]*["”]/g,'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
  return /^(?:(?:por favor|puedes|please|can you)\s+)?(?:ayudame|acompaname|help me|assist me)\b/.test(text)&&/\b(?:en tiempo real|mientras (?:escribo|programo)|in real time|while (?:coding|i type))\b/.test(text)&&! /\b(?:no|sin|don't|do not|never)\b/.test(text);
}

// Project/resource requests go through a complete, reviewable disk plan.
export function requestsFileChanges(question){
  const text=String(question).replace(/```[\s\S]*?(?:```|$)/g,'').replace(/^\s*>.*$/gm,'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const direct=/^\s*[¿¡]?\s*(?:(?:por favor|puedes|podrias|quiero que|necesito que|please|can you|could you)\s+)*(?:crea|crear|crees|genera|generar|generes|escribe|escribir|escribas|reescribe|modifica|modificar|modifiques|edita|editar|edites|actualiza|actualizar|actualices|cambia|cambiar|cambies|anade|anadas|implementa|borra|borrar|borres|elimina|eliminar|elimines|suprime|create|generate|write|rewrite|edit|update|change|add|implement|delete|remove)\b/.test(text);
  return direct&&(/\b(?:archivo[s]?|carpeta[s]?|proyecto[s]?|file[s]?|folder[s]?|project[s]?)\b/.test(text)||/(?:^|[\s"'`(])(?:[\w@-]+[\/\\])*[\w@-]+\.[\w.-]+(?:$|[\s"'`,:).!?])/.test(text));
}
