#!/usr/bin/python
# ------------------------------------------------------------------------
#   test_fullword.py
#       WRW 22 March 2022 - Cleaning up a bit.
#   This is for testing the fullword C module.
# ------------------------------------------------------------------------

import sys
import fullword
# print( dir( fullword ) )
# print( help( fullword ) )

test_titles= [
    "This has  multiple    spaces",
    "This has spaces at end   ",
    "   And spaces at beginning",
    "This is a very long titles line that should exceed the test buffer length. Let's be sure it is really long",
    "'Round Midnight",
    "'S Wonderful",
    "After You",
    "Again",
    "Agua De Beber (Water To Drink)",
    "Agua De Beber (Water To Drink).mid",
    "Agua De Beber (Water To Drink).pdf",
    "Ain't No Sunshine",
    "Ain't No Sunshine.mid",
    "Ain't No Sunshine.pdf",
    "Alice In Wonderland",
    "All About Ronnie",
    "All My Tomorrows",
    "All Of You",
    "All Of You (Bill Evans)",
    "All The Way",
    "All Through The Night",
    "Alone Together",
    "Am I Blue?",
    "And The Angels Sing.",
    "Sing",
    "Sing.",
    ".Sing",
    "Anything Goes",
    "As Time Goes By",
    "As We Speak",
    "At Last",
    "At Long Last Love",
    "Autumn Nocturne",
    "Bags' Groove",
    "Baltimore Oriole",
    "A Beautiful Friendship",
    "Begin The Beguine",
    "Bess, You Is My Woman",
    "The Best Is Yet To Come",
    "Bewitched",
    "Bidin' My Time",
    "'Way Down Yonder In New Orleans",
    "Arriba!",
]

test_words = [
    "new",
    "foobar",
    "This is a very long words line that should exceed the test buffer length. Let's be sure it is really long",
    "bess you is my woman",
    "beber",
    "drink",
    "sing",
    "ain't sunshine",
    "Alice",
    "oriole",
    "as",
    "woman",
    "'round",
    "mid",
    ".mid",
    "'Way Down Yonder In New Orleans",
    "arriba",
    "arriba!",
]

for words in test_words:
    print( "Test:", words )
    for data in test_titles:
        try:
            if fullword.match( data, words ):
                print( "   Match:", data )

        except Exception as e:
            (extype, value, traceback) = sys.exc_info()
            print( f"ERROR on my_match_c(), type: {extype}, value: {value}", file=sys.stderr )
            print( f"  Data: {data}", file=sys.stderr  )
            print( f"  Words: {words}", file=sys.stderr  )
            sys.exit(1)
