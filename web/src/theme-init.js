try {
    const requested = new URLSearchParams(location.search).get('theme');
    const saved = localStorage.getItem('lumen.theme');
    const initial=document.documentElement.dataset.initialTheme;
    const theme = requested || initial || saved || 'day';
    document.documentElement.dataset.theme = ['day', 'dark', 'forest'].includes(theme) ? theme : 'day';
    if(!requested)globalThis.ZenitThemeAppearance.restore(document.documentElement,localStorage,initial?document.documentElement.dataset.initialExtensionTheme||'':undefined);
} catch (_) {
    document.documentElement.dataset.theme = 'day';
}
