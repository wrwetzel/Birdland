<?php
    // ---------------------------------------------------------------------------------------------
    // WRW 2 June 2022 - Trying to put together a simple Birdland search function
    // for online use. Extracted bits and pieces from PogoData but stripped out
    // the class structures. Unneeded for something this small.
    // error_log( print_r( val, True ));
    // ---------------------------------------------------------------------------------------------

    require_once( "/home/wrw/PHP/birdland.php" );

    // -------------------------------

    try {
        $conn = new PDO( "mysql:host={$birdland_Host};dbname={$birdland_DB};charset=utf8",
                         $birdland_User,
                         $birdland_Pass,
                         array( PDO::ATTR_EMULATE_PREPARES => false,                 // WRW 6 June 2022 - try true for multiple selects.
                                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION )
                       );
    }
    catch( PDOException $ex ) {
        $emsg = $ex->getMessage();
        $error = "ERROR 1: $emsg";
        $ret = [ 'error' => $error, 'query' => '' ];
        echo json_encode( $ret );
        exit( 0 );
    }

    // -------------------------------

    $title = $composer = $lyricist = $artist = $album = Null;

    $limit = 25;                                // Default, overridden by $.ajax() call argument.

    foreach($_REQUEST as $k => $v) {            /// RESUME better way to get all args insead of loop
        if( $v == '' ) {
            continue;
        }

        switch( $k ) {                          // Replaced chain of if statements with switch.
        case 'type':
            $search_type = $v;
            break;

        case 'limit':
            $limit = $v;
            break;

        case 'title':
            $title = $v;
            break;

        case 'composer':
            $composer = $v;
            break;

        case 'lyricist':
            $lyricist = $v;
            break;

        case 'artist':
            $artist = $v;
            break;

        case 'album':
            $album = $v;
            break;

        default:
            $ret = [ 'error' => "ERROR: Unexpected value in request '{$k}'", 'query' => '' ];
            echo json_encode( $ret );
            exit( 0 );
        }
    }

    // ---------------------------------------------------------------------------------------

    if( $search_type == "music-search" ) {
        music_search( $conn, $title, $composer, $lyricist, $artist, $album, $limit );
    } 

    if( $search_type == "audio-search" ) {
        audio_search( $conn, $title, $artist, $album, $limit );
    }

    if( $search_type == "indexed-books" ) {
        get_books( $conn );
    }

    // ---------------------------------------------------------------------------------------

    function music_search( $conn, $title, $composer, $lyricist, $artist, $album, $limit ) {

        $where = [];
        $binding = [];
        $more_select = "";
        $more_join= "";
        $aa_flag = False;

        if( $title ) {
            $where[] = "MATCH( title ) AGAINST( :title IN BOOLEAN MODE )";
            $binding[ ':title' ] = $title;

        }
        if( $composer ) {
            $where[] = "composer LIKE :composer";
            $binding[ ':composer' ] = "%{$composer}%";
        }
        if( $lyricist ) {
            $where[] = "lyricist LIKE :lyricist";
            $binding[ ':lyricist' ] = "%{$lyricist}%";
        }

        if( $artist ) {
            $where[] = "titles_distinct.title IN
                            ( SELECT title FROM audio_files
                              WHERE MATCH( artist ) AGAINST( :artist IN BOOLEAN MODE ) )
                        ";
            $binding[ ':artist' ] = $artist;
        }

        if( $album) {
            $where[] = "titles_distinct.title IN
                            ( SELECT title FROM audio_files
                              WHERE MATCH( album ) AGAINST( :album IN BOOLEAN MODE ) )
                        ";
            $binding[ ':album' ] = $album;
        }

        if( $artist || $album ) {
            $aa_flag = True;
            $more_select = ", artist, album ";
            $more_join = " LEFT JOIN audio_files USING( title ) ";
            $more_join = " JOIN audio_files USING( title ) ";
        }

        // ------------------------------------------------------------

        if( $where ) {
            $where_clause = "WHERE " . join( " AND ", $where );
        } else {
            $where_clause = "";
        }

        // ------------------------------------------------------------
        //  Select rows matching search parameters

        $query = "SELECT title, composer, lyricist, canonical, sheet, titles.src
                  $more_select
                  FROM titles_distinct
                  JOIN titles USING( title_id )
                  JOIN local2canonical USING( src, local )
                  $more_join
                  $where_clause
                  ORDER BY title
                  LIMIT $limit
                ";

        try {
            $stmt = $conn->prepare( $query );
            $stmt->execute( $binding );
        }

        catch( PDOException $ex ) {
            $emsg = $ex->getMessage();
            $binding_text = join( "<br>", $binding );

            $ret = [ 'error' => "ERROR: SELECT failed, $emsg", 'query' => $query, 'binding' => $binding_text ];
            echo json_encode( $ret );
            exit( 0 );
        }

        // -----------------------------------------------------------
        //  Success, build results

        $results = [];
        while( $row = $stmt->fetch(PDO::FETCH_ASSOC )) {
            $partial_results = [ $row[ 'title' ],
                                 $row[ 'composer' ],
                                 $row[ 'lyricist' ],
                                 $row[ 'canonical' ],
                                 $row[ 'sheet' ],
                                 $row[ 'src' ]
                               ];
            if( $aa_flag ) {
                $partial_results = array_merge( $partial_results, [ $row[ 'artist' ], $row[ 'album' ] ] );
            }
            $results[] = $partial_results;
        }

        // ------------------------------------------------------------
        //  Get total count of records matching search parameters.

        $query = "SELECT COUNT(*) cnt
                  FROM titles_distinct
                  JOIN titles USING( title_id )
                  JOIN local2canonical USING( src, local )
                  $more_join
                  $where_clause
                ";

        try {
            $stmt = $conn->prepare( $query );
            $stmt->execute( $binding );
        }

        catch( PDOException $ex ) {
            $emsg = $ex->getMessage();
            $binding_text = join( "<br>", $binding );

            $ret = [ 'error' => "ERROR: SELECT COUNT(*) failed, $emsg", 'query' => $query, 'binding' => $binding_text ];
            echo json_encode( $ret );
            exit( 0 );
        }

        $row = $stmt->fetch(PDO::FETCH_ASSOC );
        $count = $row[ 'cnt' ];

        // ------------------------------------------------------------
        //  Success, return results.

        // $binding_text = join( "<br>", $binding );

        $ret = [ 'error' => '', 'results' => $results, 'count' => $count, 'aa_flag' => $aa_flag ];
        echo json_encode( $ret );
        exit( 0 );
    }

    // ---------------------------------------------------------------------------------------

    function audio_search( $conn, $title, $artist, $album, $limit ) {

        $where = [];
        $binding = [];

        if( $title ) {
            $where[] = "MATCH( title ) AGAINST( :title IN BOOLEAN MODE )";
            $binding[ ':title' ] = $title;
        }

        if( $artist ) {
            $where[] = "MATCH( artist ) AGAINST( :artist IN BOOLEAN MODE )";
            $binding[ ':artist' ] = $artist;
        }

        if( $album) {
            $where[] = "MATCH( album ) AGAINST( :album IN BOOLEAN MODE )";
            $binding[ ':album' ] = $album;
        }

        // ------------------------------------------------------------

        if( $where ) {
            $where_clause = "WHERE " . join( " AND ", $where );
        } else {
            $where_clause = "";
        }

        // ------------------------------------------------------------
        //  Select rows matching search parameters
        //  Multiple SELECT seemed like a good idea but is not supported by PDO
        //      even with PDO::ATTR_EMULATE_PREPARES = true

        // $query = "

        //     SELECT '<table class=results> <tr> <th>Title</th> <th>Artist</th> <th>Album</th> </tr>';
        //     SELECT '<tr> <td>', title, '</td><td>', artist, '</td><td>', album, '</td> </tr>'
        //     FROM audio_files
        //     $where_clause
        //     ORDER BY title
        //     LIMIT $limit;
        //     SELECT '</table>';
        // ";

        $query = "
            SELECT title, artist, album
            FROM audio_files
            $where_clause
            ORDER BY title
            LIMIT $limit
            ;
        ";
        try {
            $stmt = $conn->prepare( $query );
            $stmt->execute( $binding );
        }

        catch( PDOException $ex ) {
            $emsg = $ex->getMessage();
            $binding_text = join( "<br>", $binding );
            $ret = [ 'error' => "ERROR: SELECT failed, $emsg", 'query' => $query, 'binding' => $binding_text ];
            echo json_encode( $ret );
            exit( 0 );
        }

        // -----------------------------------------------------------
        //  Success, build results

        $results = [];
        while( $row = $stmt->fetch(PDO::FETCH_ASSOC )) {
            $results[] = [ $row[ 'title' ],
                           $row[ 'artist' ],
                           $row[ 'album' ]
                         ];
        }

        // ------------------------------------------------------------
        //  Get total count of records matching search parameters.

        $query = "SELECT COUNT(*) cnt
                  FROM audio_files
                  $where_clause
                ";

        try {
            $stmt = $conn->prepare( $query );
            $stmt->execute( $binding );
        }

        catch( PDOException $ex ) {
            $emsg = $ex->getMessage();
            $binding_text = join( "<br>", $binding );
            $ret = [ 'error' => "ERROR: SELECT COUNT(*) failed, $emsg", 'query' => $query, 'binding' => $binding_text ];
            echo json_encode( $ret );
            exit( 0 );
        }

        $row = $stmt->fetch(PDO::FETCH_ASSOC );
        $count = $row[ 'cnt' ];

        // ------------------------------------------------------------
        //  Success, return results.

        // $binding_text = join( "<br>", $binding );

        $ret = [ 'error' => '', 'results' => $results, 'count' => $count ];
        echo json_encode( $ret );
        exit( 0 );
    }

    // ---------------------------------------------------------------------------------------

    function get_books( $conn ) {
        $query = "
            SELECT src, canonical
            FROM local2canonical
            ORDER BY canonical, src
            ;
        ";
        try {
            $stmt = $conn->prepare( $query );
            $stmt->execute();
        }

        catch( PDOException $ex ) {
            $emsg = $ex->getMessage();
            $ret = [ 'error' => "ERROR: SELECT failed, $emsg", 'query' => $query ];
            echo json_encode( $ret );
            exit( 0 );
        }

        // -----------------------------------------------------------
        //  Success, build results

        $src_table = [];

        while( $row = $stmt->fetch(PDO::FETCH_ASSOC )) {
            $src = $row[ 'src' ];
            $canonical = $row[ 'canonical' ];

            if( ! array_key_exists( $canonical, $src_table )){
               $src_table[$canonical] = [];
            }       
            $src_table[$canonical][] = $src;
        }

        $results = '';
        $results .= '<p></p>';                  // since no count message.
        $results .= '<table class=results>';
        $results .= "<tr><th>Index Src</th><th>Canonical Book Name</th></tr>";

        foreach( $src_table as $canonical => $srcs ) {
            $t = join( ' ', $srcs );
            $results .= "<tr>";
            $results .= "<td>{$t}</td><td>{$canonical}</td>";
            $results .= "</tr>";
        }

        $results .= '</table>';

        $ret = [ 'error' => '', 'results' => $results ];
        echo json_encode( $ret );
        exit( 0 );
    }

    // ---------------------------------------------------------------------------------------

    function old_get_books( $conn ) {
        $query = "
            SELECT count(*) cnt, canonical
            FROM local2canonical
            GROUP BY canonical
            ORDER BY cnt DESC, canonical
            ;
        ";
        try {
            $stmt = $conn->prepare( $query );
            $stmt->execute();
        }

        catch( PDOException $ex ) {
            $emsg = $ex->getMessage();
            $ret = [ 'error' => "ERROR: SELECT failed, $emsg", 'query' => $query ];
            echo json_encode( $ret );
            exit( 0 );
        }

        // -----------------------------------------------------------
        //  Success, build results

        $results = '';
        $results .= '<p></p>';                  // since no count message.
        $results .= '<table class=results>';
        $results .= "<tr><th>Index Src Count</th><th>Canonical Book Name</th></tr>";

        while( $row = $stmt->fetch(PDO::FETCH_ASSOC )) {
            $results .= "<tr>";
            $results .= "<td>{$row[ 'cnt' ]}</td><td>{$row[ 'canonical' ]}</td>";
            $results .= "</tr>";
        }

        $results .= '</table>';

        $ret = [ 'error' => '', 'results' => $results ];
        echo json_encode( $ret );
        exit( 0 );
    }
?>
