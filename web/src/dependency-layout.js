import {icon} from './icons.js';

/** One aligned working surface for all package managers. */
export function mountDependencyLayout(root,p){
  const t=p.t.bind(p),native=root.classList.contains('native-packages');
  root.classList.add('dependency-workspace');
  const grid=document.createElement('div');grid.className='dependency-grid';
  const setup=document.createElement('section');setup.className='dependency-setup';
  const inventory=document.createElement('section');inventory.className='dependency-inventory';
  const title=document.createElement('h4');title.innerHTML=icon('files')+t('Dependencias del proyecto','Project dependencies');inventory.append(title);
  for(const selector of ['.python-environment','.native-tools','.python-feedback','.python-install','.python-actions','.python-task']){const node=root.querySelector(selector);if(node)setup.append(node);}
  for(const selector of ['.python-list-toolbar','.python-package-list']){const node=root.querySelector(selector);if(node)inventory.append(node);}
  grid.append(setup,inventory);root.querySelector('.python-footnote').before(grid);
  const mark=document.createElement('span');mark.className='dependency-mark';mark.innerHTML=icon(native?'cpu':'code');root.querySelector('.python-heading').prepend(mark);
}
