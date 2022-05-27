/* ---------------------------------------------------------------------------------------- */
/*  WRW 17 Feb 2022 - This implements an approximation of MySql FULLTEXT search in C.
    The Sqlite3 implementation of FULLTEXT did not work well. It might be my own doing
    but I couldn't get good results and often outright failure on some input values.
    I explores several approaches as shown in fb_utils.py before implementing this in C.
    Works great.

    Starting point was examples in Python docs:
        https://docs.python.org/3/extending/extending.html

    Called with two strings: column and value. Column from the equivalent MySql MATCH( column ).
    Value from the equivalent of MySql AGAINST( value ) and is constant over many calls.

    Divide column strings on white space and several other separators and value string on just white space.
    Build a list of pointers to beginning of divided strings.

    A little optimization by caching value since that changes only once per search whereas column changes
        with every row of table.                                         

    Cheating a little here with fixed size buffers and lists but with a 2:1 safety margin over longest string seen.
    Maybe someday do with dynamic buffer. Overflows are detected and reported with an exception.

    Note: ignore_word are not implemented yet. Maybe never.

    WRW 2 May 2022 - Rewriting some of this for better clarity. 
        Saved last working version in fullwordmodule.c.pre-2-may-2022-work.
        The #ifdefs were getting to messy, redo this without worrying about going back. Have saved version.
        Primary changes:
            Refactor into several functions.
            Break and ignore chars are in strings instead of if() stmts.
            Use break and ignore chars consistently on both column and value.
            Add cache code to only process value when it changes.
*/
/* ---------------------------------------------------------------------------------------- */

#define PY_SSIZE_T_CLEAN
#include <python3.10/Python.h>

// #define DEBUG    // Enables printf() of column, value before and after filtering and lists after partitioning

#ifdef DEBUG
    #include <stdio.h>
#endif

static PyObject *MatchError;
void do_exception();

#define LIST_SIZE 80                    // Maximum number of tokens in column or value.  Saw 38 tokens.
#define BUF_SIZE  500                   // 500 Maximum string length for column or value. Saw 254 bytes.

char cached_value[ BUF_SIZE ] = "Y";    // Cache copy of original string. value_buf is partioned into separate strings and not suitable for strcmp().
char *value_list[ LIST_SIZE ];          // Cache value list in global space
char value_buf[ BUF_SIZE ] = "X";       // Cache value string in global space. "X" and "Y" needed to fail initial strcmp().
int value_cnt;                          // Global for access on cache hit.

char *ignore_chars = "\"!?()";          // chars ignored in value and column when matching
char *break_chars  = "_-/,.";           // value and column are partitioned into separate words on these chars and space.

// ----------------------------------------------------------------------------------------   
//  A few functions used for both column and value. Originally inline. Now much cleaner.
// ----------------------------------------------------------------------------------------   
//  Return 1 if char c found in string s. Used for dealing with ignore_chars and break_chars

int char_in_string( char c, char *s ) {
    char x;

    while( (x = *s++) ) if( c == x ) return 1;
    return 0;
}

// ---------------------------------------------------------------------
//  Split 'buf' into separate words on space boundaries.
//      Create list of pointers to words in 'list'
//      Return count of words or -1 on error.

int partition_buffer( char *id, char *buf, char **list ) {
    int count = 0;
    int i;
    char c;

    list[ count++ ] = &buf[0];

    for( i = 0; (c = buf[i]); i++ ) {
        if( c == ' ' ) {
            buf[i] = 0x00;                      // Terminate word in buffer
            list[ count++ ] = &buf[i+1];        // And add next word to list

            if( count >= LIST_SIZE ) {
                sprintf( buf, "%s token count exceeds internal limit: %d", id, LIST_SIZE );
                do_exception( buf );
                return -1;
            }
        }
    }
    return count;
}

// ---------------------------------------------------------------------
//  Copy 'src' to 'dst' ignoring some some chars, converting others to space.

void copy_to_buffer( const char *src, char *dst ) {
    int prior_c = 0xff;
    int i, j;
    char c;

    for( i=0, j=0; ( c = tolower( src[i] )); i++ ) {
        if( char_in_string( c, ignore_chars )) continue;    // Ignore ignore_chars
        if( char_in_string( c, break_chars )) c = ' ';      // Translate break_chars to space
        if( c == ' ' && j == 0 ) continue;                  // Ignore leading space
        if( c == ' ' && c == prior_c ) continue;            // Collapse successive spaces to one.
        dst[ j++ ] = c;
        prior_c = c;
    }
    if( j > 0 && dst[ j-1 ] == ' ' ) {
        dst[ j-1 ] = 0x00;          // Remove possible trailing space residual from collapsing multiple trailing spaces.
    } else {
        dst[ j ] = 0x00;            // Terminate output string
    }
}

// ---------------------------------------------------------------------
// PyArg_ParseTuple second arg: z: str or None, s: str,
//      There are some Nulls at least in the audio_file table, maybe elsewhere when no column.
//      Arrive here as None. Return if so as can't do anything.

static PyObject *
fullword_match( PyObject *self, PyObject *column_args, PyObject *value_args ) {
    const char * column;
    const char * value;

    if (!PyArg_ParseTuple(column_args, "zs", &column, &value )) {       // This gets column and value from fullword_match() args.
        return NULL;
    }

    if( ! column ) {                          // Fields in database can have Null values.
        return PyLong_FromLong( 0 );
    }

    #ifdef DEBUG
        // setbuf(stdout, NULL);            // To force flush when isolating segfault.
        printf( "----------------------------------------\n" );
    #endif

    // ---------------------------------------------------------------------
    //  Lenght checks on column and value

    char column_buf[ BUF_SIZE ];          // temp column on stack so don't have to worry about free() if malloc()ed.
    char *column_list[LIST_SIZE];         // also use column_buf for exception messages.

    if( strlen( column ) > BUF_SIZE ) {
        sprintf( column_buf, "Column data length exceeds internal limit: %d", BUF_SIZE );
        do_exception( column_buf );
        return NULL;
    }

    if( strlen( value ) > BUF_SIZE ) {
        sprintf( column_buf, "Value data length exceeds internal limit: %d", BUF_SIZE );
        do_exception( column_buf );
        return NULL;
    }

    // -----------------------------------------------------------------
    //  Value cache.
    //  Only copy_to_buffer() and partition_buffer() when value changes.

    if( strcmp( value, cached_value )) {        // This one strcmp() and strcpy() should be faster than
        strcpy( cached_value, value );          // several copy_to_buffer() and partition_buffer() on each iteration.

        copy_to_buffer( value, value_buf );

        #ifdef DEBUG
            printf( "value: '%s'\n", value );
            printf( "value_buf: '%s'\n", value_buf );
        #endif

        value_cnt = partition_buffer( "Value", value_buf, value_list );         //  Split value on space into list
        if( value_cnt < 0 ) {
            return NULL;
        }
    }       

    int column_cnt;

    copy_to_buffer( column, column_buf );
    #ifdef DEBUG
        printf( "column: '%s'\n", column );
        printf( "column_buf: '%s'\n", column_buf );
    #endif

    column_cnt = partition_buffer( "Column", column_buf, column_list );            //  Split column on space into list
    if( column_cnt < 0 ) {
        return NULL;
    }

    // -----------------------------------------------------------------
    //  Diagnostics

    #ifdef DEBUG
        {
            int i;
            for( i = 0; (i < value_cnt); i++ ) {                          // for each token in value (the search value)
                printf( "value_list: '%s'\n", value_list[i] );
            }

            for( i = 0; (i < column_cnt); i++ ) {                          // for each token in value (the search value)
                printf( "column_list: '%s'\n", column_list[i] );
            }
            printf( "\n" );
        }
    #endif

    // -----------------------------------------------------------------
    //  Finally, approximate "MATCH( column ) AGAINST( value ) IN BOOLEAN MODE" from mysql.
    //  Match in value in order given.

    int i;
    int j;
    int next_i = 0;
    int match;
    int matches = 0;

    for( j = 0; j < column_cnt; j++ ) {                         // for each token in column (the column value )
        for( i = next_i; (i < value_cnt); i++ ) {               // for each token in value (the search value )
            if( ! strcmp( value_list[i], column_list[j] )) {    // found word in column, stop looking for word
                matches++;
                next_i = i + 1;                                 // Start next iteration of value where left off in previous.
                break;
            }
        }
    }

    /* ----------------------------------------- */
    //  All values must match.

    if( value_cnt == matches ) {
        match = 1;
    } else {
        match = 0;
    }

    /* ----------------------------------------- */

    return PyLong_FromLong( match );
}

// ----------------------------------------------------------------------------------------   

void do_exception( char * s ) {
    PyErr_SetString(MatchError, s );
}

// ----------------------------------------------------------------------------------------   
//  Must cast fullword_match ( type of PyObject ) to PyCFunction below to suppress compiler warning.
//  *** The method "match" is named here.

static PyMethodDef FullWordMethods[] = {
    {"match", ( PyCFunction ) fullword_match, METH_VARARGS, "Execute a simpliflied equivalent of MySql MATCH( column ) AGAINST( value ) IN BOOLEAN MODE"},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

// ----------------------------------------------------------------------------------------   

static struct PyModuleDef fullwordmodule = {
    PyModuleDef_HEAD_INIT,
    "fullword",             /* name of module. *** The module is named here */
    NULL,                   /* module documentation, may be NULL */
    -1,                     /* size of per-interpreter state of the module,
                               or -1 if the module keeps state in global variables. */
    FullWordMethods
};

// ----------------------------------------------------------------------------------------   
//  Don't know what this is all about yet. Have to read more of the documentation.

PyMODINIT_FUNC
PyInit_fullword(void)
{
    PyObject *m;

    m = PyModule_Create( &fullwordmodule );
    if (m == NULL)
        return NULL;

    MatchError = PyErr_NewException( "match.error", NULL, NULL);
    Py_XINCREF(MatchError);
    if (PyModule_AddObject(m, "error", MatchError ) < 0) {
        Py_XDECREF(MatchError);
        Py_CLEAR(MatchError);
        Py_DECREF(m);
        return NULL;
    }
    return m;
}

// ----------------------------------------------------------------------------------------   
