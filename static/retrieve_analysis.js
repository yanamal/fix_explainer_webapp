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
                //add_exercise_link(result.chapter, result.practice_url, result.exercise_url, result.num_exercises)
                if(result.practice_problems.length > 0) {
                    add_practice_links(result.practice_problems)
                }

                // TODO: redundant because load_sequence_data already does it?..
                highlight_nodes()
                apply_special_styling()

                log_clicks("#tab-titles>li")
                log_clicks("#animate-button")
                log_hovers(".ast-node")
            }
            else if(result.result_type=="Syntax Error") {
                $('#animate-button').hide()
                $('#error-header').text('Syntax Error')
                $('#bad-code').text(result.analysis.code)
                $('#error-message').text(result.analysis.message)
                if(result.practice_problems.length > 0) {
                    add_practice_links(result.practice_problems)
                }
                point_to_syntax_error(result.analysis.lineno, result.analysis.offset)
            }

            // logging that should happen in all cases:
            log_clicks("#report_button")
            log_clicks('#is_helpful label')

            // Log the fact that the page has loaded
            log_custom_event("page_load", {})
            send_logs()

            // log visibility change events
            // also, send logs on window close/other hidden state
            document.addEventListener("visibilitychange", function logData() {
                if (document.visibilityState === "hidden") {
                    // TODO: why does this trigger long before the retrieve completes even though I'm adding listener on retrieve?
                    //   also, why does navigate_away trigger on page load at all?
                    log_custom_event("navigate_away", {})
                    send_logs()
                }
                else {
                    log_custom_event("navigate_to", {})
                }
            })

            // send logs every 10 seconds [TODO: after last send?]
            window.setInterval(function(){
                if(event_cache.length > 0){
                    send_logs()
                }
            }, 10000);

            // send logs on (fix explainer) tab change
        }
    });
}

function add_practice_links(practice_problems){
    $('#practice_links').append("<div>Practice problems that address common issues with this homework problem:</div>")
    for(p of practice_problems){
      $('#practice_links').append(`<div><a href=${p.url} target="_blank">${p.description}</a></div>`)
    }
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

$( document ).ready(function() {
    bug_diaog = $('#bug_report').dialog({
      autoOpen: false,
    //   height: 400,
      width: 600,
      modal: true,
      buttons: {
        "Sumbit bug report": function(){
            $.ajax({
                type: "POST",
                url: "/feedback",
                data: Object.fromEntries(new FormData($("#bug_form")[0]))
            })
            bug_diaog.dialog( "close" );
        }
      }
    });

    $( "#report_button" ).button().on( "click", function() {
      bug_diaog.dialog( "open" );
    });

    $('#is_helpful input').checkboxradio()
});