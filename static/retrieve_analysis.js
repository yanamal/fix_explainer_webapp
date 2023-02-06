function load_data_from_db(help_request_id){
    $.ajax({
        type: "POST",
        url: "/retrieve",
        data: {
            request_id: help_request_id,
        },
        success: function(result) {
            console.log(result);
            if(result.result_type=="Fixes Generated" || result.result_type=="Analysis Generated") { // whoopsie, changed the identifier string in the middle of using the database
                //$( "#code-div" ).tabs( "destroy" ); // TODO: move back to loading logic, make sure tabs exist first somehow
                load_sequence_data(result.analysis)
                highlight_nodes()
                apply_special_styling()
            }
            else if(result.result_type=="Syntax Error") {
                $('#animate-button').hide()
                $('#error-header').text('Syntax Error')
                $('#bad-code').text(result.analysis.code)
                $('#error-message').text(result.analysis.message)
                point_to_syntax_error(result.analysis.lineno, result.analysis.offset)
            }
        }
    });
}


// TODO: unify the 3 slightly different implementations of point_to_syntax_error?
function point_to_syntax_error(lineno, offset) {
    lineno -= 1  // lineno is 1-indexed but we don't need that
    offset -= 1  // offset also?..
    bad_code_lines = $('#bad-code').text().split('\n')
    bad_code_lines[lineno] = bad_code_lines[lineno].slice(0, offset) + '<span id="error-pos"></span>' + bad_code_lines[lineno].slice(offset)
    $('#bad-code').html(bad_code_lines.join('\n'))
    new LeaderLine(
        $('#error-message')[0],
        $('#error-pos')[0],
        {
            endSocket: 'top',
            color: 'rgba(255, 0, 0, 0.5)',
            dash: true,
            size: 2,
        }
    )
}