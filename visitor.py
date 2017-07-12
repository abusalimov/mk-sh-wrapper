from bashlex.ast import node


class NodeVisitor:
    def _visit(self, n, *args, **kwargs):
        method_name = 'visit_' + n.kind
        visitor = getattr(self, method_name)
        return visitor(n, *args, **kwargs)

    def _visit_children(self, *children):
        if len(children) == 1:
            return self.visit(children[0])
        for n in children:
            self.visit(n)

    def _visit_parts(self, parts):
        return [self.visit(part) for part in parts]


    def visit(self, n, **kwargs):
        if isinstance(n, list):
            return self._visit_children(*n, **kwargs)
        if not isinstance(n, node):
            return n

        k = n.kind
        if k == 'operator':
            return self._visit(n, n.op, **kwargs)
        if k == 'list':
            return self._visit(n, n.parts, **kwargs)
        if k == 'reservedword':
            return self._visit(n, n.word, **kwargs)
        if k == 'pipe':
            return self._visit(n, n.pipe, **kwargs)
        if k == 'pipeline':
            return self._visit(n, n.parts, **kwargs)
        if k == 'compound':
            return self._visit(n, n.list, n.redirects, **kwargs)
        if k in ('if', 'for', 'while', 'until'):
            return self._visit(n, n.parts, **kwargs)
        if k == 'command':
            return self._visit(n, n.parts, **kwargs)
        if k == 'function':
            return self._visit(n, n.name, n.body, n.parts, **kwargs)
        if k == 'redirect':
            return self._visit(n, n.input, n.type, n.output, n.heredoc, **kwargs)
        if k in ('word', 'assignment'):
            return self._visit(n, n.word, **kwargs)
        if k == 'wordtext':
            return self._visit(n, n.text, **kwargs)
        if k in ('parameter', 'tilde', 'heredoc'):
            return self._visit(n, n.value, **kwargs)
        if k in ('commandsubstitution', 'processsubstitution'):
            return self._visit(n, n.command, **kwargs)

        raise ValueError('unknown node kind %r' % k)

    def visit_operator(self, node, op, **kwargs):
        return self._visit_children(op)
    def visit_list(self, node, parts, **kwargs):
        return self._visit_children(parts)
    def visit_pipe(self, node, pipe, **kwargs):
        return self._visit_children(pipe)
    def visit_pipeline(self, node, parts, **kwargs):
        return self._visit_children(parts)
    def visit_compound(self, node, list_, redirects, **kwargs):
        return self._visit_children(list_, redirects)
    def visit_if(self, node, parts, **kwargs):
        return self._visit_children(parts)
    def visit_for(self, node, parts, **kwargs):
        return self._visit_children(parts)
    def visit_while(self, node, parts, **kwargs):
        return self._visit_children(parts)
    def visit_until(self, node, parts, **kwargs):
        return self._visit_children(parts)
    def visit_command(self, node, parts, **kwargs):
        return self._visit_children(parts)
    def visit_function(self, node, name, body, parts, **kwargs):
        return self._visit_children(name, body, parts)
    def visit_word(self, node, word, **kwargs):
        return self._visit_children(word)
    def visit_wordtext(self, node, text, **kwargs):
        return self._visit_children(text)
    def visit_assignment(self, node, word, **kwargs):
        return self._visit_children(word)
    def visit_reservedword(self, node, word, **kwargs):
        return self._visit_children(word)
    def visit_parameter(self, node, value, **kwargs):
        return self._visit_children(value)
    def visit_tilde(self, node, value, **kwargs):
        return self._visit_children(value)
    def visit_redirect(self, node, input_, type_, output, heredoc, **kwargs):
        return self._visit_children(input_, type_, output, heredoc)
    def visit_heredoc(self, node, value, **kwargs):
        return self._visit_children(value)
    def visit_processsubstitution(self, node, command, **kwargs):
        return self._visit_children(command)
    def visit_commandsubstitution(self, node, command, **kwargs):
        return self._visit_children(command)

