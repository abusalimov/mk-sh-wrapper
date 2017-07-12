#!/usr/bin/env python3

import io
import os
from sh import Command, ErrorReturnCode
import sys
from contextlib import contextmanager
from pprint import pprint

import bashlex

from visitor import NodeVisitor


def dprint(*args):
    print(*args, file=sys.stderr)


class BashEvalError(Exception):
    pass


class CommandExit(BashEvalError):
    def __init__(self, code):
        self.code = code


class OperatorExit(CommandExit):
    pass


class StackMeter:
    def __init__(self, depth=0):
        super().__init__()
        self.depth = depth

    def __enter__(self):
        depth = self.depth
        self.depth += 1
        return depth

    def __exit__(self, *exc_info):
        self.depth -= 1


class BashEvalVisitor(NodeVisitor):
    def __init__(self, environ={}, cwd='.', stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
        self.variables = dict(environ)
        self.exports = set(environ)
        self.cwd = os.path.abspath(cwd)
        self.oldcwd = None
        self.stdin = io.StringIO()
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.exitcode = 0

        setattr(self, 'do_:', lambda *args: 0)

        self._stack_meter = StackMeter()

    @contextmanager
    def capture_stdout(self):
        oldstdout = self.stdout
        self.stdout = io.StringIO()
        try:
            yield self.stdout
        finally:
            self.stdout = oldstdout

    def outln(self, s):
        print(s, file=self.stdout)
        return 0

    def _visit(self, n, *args, **kwargs):
        with self._stack_meter as depth:
            for attr in ('word', 'text', 'op', 'value'):
                if hasattr(n, attr):
                    s = '<- ' + getattr(n, attr)
                    break
            else:
                s = ''
            dprint(('╿ ' * depth) + '┌─', n.kind, s)
            try:
                ret = super()._visit(n, *args, **kwargs)
            except Exception as e:
                dprint(('╿ ' * depth) + '└─', n.kind, '##', e)
                raise e
            else:
                dprint(('╿ ' * depth) + '└─', n.kind, '->', ret if n.kind != 'command' else self.stdout.getvalue())
            return ret

    def visit_operator(self, node, op, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_list(self, node, parts, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_pipe(self, node, pipe, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_pipeline(self, node, parts, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_compound(self, node, list_, redirects, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_if(self, node, parts, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_for(self, node, parts, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_while(self, node, parts, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_until(self, node, parts, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_command(self, node, parts, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_function(self, node, name, body, parts, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_word(self, node, word, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_wordtext(self, node, text, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_assignment(self, node, word, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_reservedword(self, node, word, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_parameter(self, node, value, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_tilde(self, node, value, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_redirect(self, node, input_, type_, output, heredoc, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_heredoc(self, node, value, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_processsubstitution(self, node, command, **kwargs):
        raise NotImplementedError(node.dump())
    def visit_commandsubstitution(self, node, command, **kwargs):
        raise NotImplementedError(node.dump())


    def visit_assignment(self, node, name, **kwargs):
        name, _, value = self.visit_word(node, name).partition('=')
        self.variables[name] = value
        return ':'

    def visit_parameter(self, node, name, **kwargs):
        name, _, default = name.partition('-')
        return self.variables.get(name, default)

    def visit_word(self, node, word, **kwargs):
        # return ''.join(self.visit(part) for part in getattr(node, 'parts', []))
        result = io.StringIO()

        for part in getattr(node, 'parts', []):
            text = self.visit(part)
            result.write(text)

        return result.getvalue()

    def visit_wordtext(self, node, text, **kwargs):
        return text

    def visit_commandsubstitution(self, node, command, **kwargs):
        subshell = self.__class__()
        subshell.variables.update(self.variables)
        subshell.exports.update(self.exports)
        subshell.cwd = self.cwd
        subshell.oldcwd = self.oldcwd
        subshell.stdin = self.stdin
        subshell.stdout = io.StringIO()
        subshell.stderr = self.stderr
        subshell.exitcode = self.exitcode

        # with self.capture_stdout() as stdout:
        subshell.visit(command)

        return (subshell.stdout.getvalue().rstrip() or ' ').replace('\n', ' ')


    def visit_pipeline(self, node, parts, **kwargs):
        for part in parts:
            if part.kind == 'pipe' and part.pipe == '|':
                self.stdin = io.StringIO(self.stdout.getvalue())
                self.stdout = io.StringIO()
            else:
                self.visit(part)

    def visit_list(self, node, parts, **kwargs):
        for part in parts:
            try:
                self.visit(part)
            except OperatorExit:
                break

    def visit_operator(self, node, op, **kwargs):
        if ((op == '&&' and self.exitcode != 0) or
            (op == '||' and self.exitcode == 0)):
            raise OperatorExit(self.exitcode)

    def visit_command(self, node, parts):
        # dprint(node.dump())
        parts = self._visit_parts(parts)
        # dprint(">>> ", parts)
        cmd = parts[0]
        try:
            do_cmd = getattr(self, 'do_' + cmd)
        except AttributeError:
            raise NIY(*parts)
        else:
            self.exitcode = int(do_cmd(*parts))

    def do_echo(self, cmd, *args):
        return self.outln(' '.join(args))

    def do_export(self, cmd, name, *args):
        if any(a.startswith('-') for a in args):
            raise NIY(cmd, *args)
        name, has_value, value = name.partition('=')
        if has_value:
            self.variables[name] = value
        self.exports.add(name)

        return 0

    def do_unset(self, cmd, name, *args):
        if any(a.startswith('-') for a in args):
            raise NIY(cmd, *args)

        self.exports.discard(name)
        self.variables.pop(name, None)

        return 0

    def do_pwd(self, cmd):
        return self.outln(self.cwd)

    def do_cd(self, cmd, directory=None):
        def cd(newcwd):
            self.oldcwd, self.cwd = self.cwd, newcwd
            return 0

        if directory == '-':
            if self.oldcwd is None:
                return -1
            return cd(self.oldcwd)

        return cd(os.path.expanduser('~' if directory is None else os.path.abspath(os.path.join(self.cwd, directory))))

    def do_sed(self, *argv):
        return self.system(*argv)

    def do_ls(self, *argv):
        return self.system(*argv)

    def do_make(self, progname, *args):
        return self.system(progname, 'SHELL={} "$(CURDIR)" "$@"'.format(sys.argv[0]), *[arg for arg in args
                                                                                        if not arg.startswith('SHELL=')])

    def system(self, progname, *args):
        dprint("EXEC" , progname, *["'{}'".format(arg) for arg in args])
        env = {k: v for k, v in self.variables.items() if k in self.exports}
        command = Command(progname)
        try:
            return command(*args,
                           _in=self.stdin,
                           _out=self.stdout,
                           _err=self.stderr,
                           _cwd=self.cwd,
                           _env=env).exit_code
        except ErrorReturnCode as e:
            return e.exit_code

#
# def get_word(node):
#     class Found(Exception):
#         def __init__(self, value):
#             self.value = value
#
#     class WordVisitor(NodeVisitor):
#         def visit_word(self, node, word, **kwargs):
#             raise Found(node)
#
#     try:
#         WordVisitor().visit(node)
#     except Found as e:
#         return e.value


def NIY(*args):
    return NotImplementedError(' '.join(args))


def eval_cmdline(cmdline, debug_file=None):
    for ast in bashlex.parse(cmdline.replace('\\\n', '  ')):
        dump = ast.dump()
        print(dump, file=debug_file)
        visitor = BashEvalVisitor(os.environ)
        visitor.visit(ast)
        sys.stdout.write(visitor.stdout.getvalue())
        sys.stderr.write(visitor.stderr.getvalue())
        print('$?: {}'.format(visitor.exitcode), file=debug_file)


def main(argv):
    if len(argv) < 5:
        print("Usage: {} CURDIR TARGET -c CMDLINE".format(argv[0]), file=sys.stderr)
        return -1

    with open('/home/user/tmp/compile-db.txt', 'a') as db:
        print(argv, file=sys.stderr)
        # pprint(dict(os.environ), stream=sys.stderr)

        progname, curdir, target, _, cmdline = argv

        eval_cmdline(cmdline, sys.stderr)

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
