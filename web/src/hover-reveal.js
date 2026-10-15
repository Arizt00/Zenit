/** The label follows the button, including interrupted hover and keyboard focus. */
export function hoverReveal(button){
  button.classList.add('hover-reveal');
  button.setAttribute('aria-label',button.title||button.textContent.trim());
  button.addEventListener('click',()=>button.classList.add('reveal-dismissed'));
  button.addEventListener('pointerleave',()=>button.classList.remove('reveal-dismissed'));
  button.addEventListener('blur',()=>button.classList.remove('reveal-dismissed'));
  return button;
}
