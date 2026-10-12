"""Format owned styles without changing selector or declaration order."""
from pathlib import Path
import tinycss2

ROOT = Path(__file__).resolve().parents[1]


def emit(rules, depth=0):
    prefix = '  ' * depth
    output = []
    for rule in rules:
        if rule.type == 'comment':
            output.append(prefix + '/*' + rule.value + '*/')
        elif rule.type == 'qualified-rule':
            selector = tinycss2.serialize(rule.prelude).strip()
            declarations = tinycss2.parse_declaration_list(rule.content, skip_whitespace=True)
            block = [prefix + selector + ' {']
            for declaration in declarations:
                if declaration.type == 'comment':
                    block.append(prefix + '  /*' + declaration.value + '*/')
                elif declaration.type == 'declaration':
                    value = tinycss2.serialize(declaration.value).strip()
                    block.append(prefix + '  ' + declaration.name + ': ' + value + (' !important' if declaration.important else '') + ';')
                else:
                    raise ValueError(declaration)
            block.append(prefix + '}')
            output.append('\n'.join(block))
        elif rule.type == 'at-rule':
            name = '@' + rule.at_keyword + ' ' + tinycss2.serialize(rule.prelude).strip()
            if rule.content is None:
                output.append(prefix + name + ';')
            else:
                output.append(prefix + name + ' {\n' + emit(tinycss2.parse_rule_list(rule.content, skip_whitespace=True), depth + 1) + '\n' + prefix + '}')
        else:
            raise ValueError(rule)
    return '\n\n'.join(output)


if __name__ == '__main__':
    for path in (ROOT / 'web/design').glob('*.css'):
        if path.name == 'support.css':
            continue
        source = tinycss2.parse_stylesheet(path.read_text(encoding='utf-8'), skip_whitespace=True)
        path.write_text(emit(source) + '\n', encoding='utf-8')
