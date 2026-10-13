import {icon} from './icons.js';

const BRANDS={codex:'openai',openai:'openai','claude-code':'claude',anthropic:'claude','gemini-cli':'googlegemini',gemini:'googlegemini',copilot:'githubcopilot',ollama:'ollama'};
export const providerName=id=>({codex:'ChatGPT',openai:'OpenAI','claude-code':'Claude',anthropic:'Claude','gemini-cli':'Gemini',gemini:'Gemini',copilot:'GitHub Copilot',emma:'Emma',ollama:'Ollama'})[id]||id;
export function providerIcon(id){const brand=BRANDS[id];return brand?`<span class="provider-brand" data-brand="${brand}" aria-hidden="true" style="--provider-mark:url('/assets/providers/${brand}.svg')"></span>`:icon('sparkles');}
export const providerKind=id=>['codex','claude-code','gemini-cli','copilot'].includes(id)?'Account':['openai','anthropic','gemini'].includes(id)?'API':'Local';
