"""Declared command icons are images scoped to the reviewed extension package."""
from pathlib import Path
import re
from .extensions import safe_member,image_data

def command_icons(root,manifest):
    root=Path(root).resolve();result={};budget=1_000_000
    def image(relative):
        if not isinstance(relative,str):return None
        path=(root/str(safe_member(relative))).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size>32000:return None
        return image_data(path.read_bytes())
    commands=manifest.get('contributes',{}).get('commands',[])
    if not isinstance(commands,list):return result
    for command in commands:
        if not isinstance(command,dict) or not isinstance(command.get('command'),str):continue
        value=command.get('icon');icon=None
        try:
            if isinstance(value,str):icon=value if re.fullmatch(r'\$\([\w-]+(?:~spin)?\)',value) else image(value)
            elif isinstance(value,dict):
                light,dark=image(value.get('light')),image(value.get('dark'));icon={'light':light or dark,'dark':dark or light} if light or dark else None
        except (OSError,ValueError,UnicodeError):continue
        if icon:
            size=len(str(icon));budget-=size
            if budget<0:break
            result[command['command']]=icon
    return result
