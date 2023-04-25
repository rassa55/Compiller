from lexer import Lexer
from parser import build_tree
#

if __name__ == "__main__":
    lst = '''program Hello;
   var a,b,c : integer
   begin
       a = 5 - 1;
       b = 10 + 6;
       c = a * b;
       print("a * b =");
       print(c)
   end.'''
    Lexer.lexer.input(lst)
    counter = 0
    while True:
        tok = Lexer.lexer.token()
        if not tok:
            break
        print(tok)

    print(build_tree(lst))
