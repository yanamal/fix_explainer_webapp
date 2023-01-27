//allow_syntax_error = false  // this can change to True if student confirms that they wanted to submit code with a syntax error.
// in that case, the server will not return a syntax_error result if there is indeed a syntax error.


function submit_handler(data){
    console.log(data)
    $('#processing').dialog("close")
    if(data.result == 'syntax_error'){
        $('#syntax-error').dialog("open")
        $('#bad-code').text(data.error.code)
        $('#error-message').text(data.error.message)
        point_to_syntax_error(data.error.lineno, data.error.offset)
    }
    else if(data.submitted){
        location.href = 'student_confirm'
    }

}


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


update_problems = function() {
    $('#problem option').addClass('inactive')
    hw = document.getElementById('homework').value
    if(hw != '') {
        $(`#problem option[data-hw=${hw}]`).removeClass('inactive')
        $(`#deselect-problem`).prop('selected', true)
    }
}


$( document ).ready(function() {

    update_problems()
    document.getElementById('homework').onchange = update_problems

    $("#request-form").validate({
        submitHandler: function(form) {
            console.log(form)
            $('#processing').dialog("open")
            $(form).ajaxSubmit({
                dataType: 'json',
                success: submit_handler,
                error: function(data) {
                    alert("Oops! something went wrong when analyzing your code. If this problem persists, please submit your help request without the code. Sorry!");
                },
            })
        }
    });

    $( "#syntax-error" ).dialog({
        autoOpen: false,
        height: "auto",
        width: "auto",
        modal: true,
        buttons: {
            "No, let me fix that before submitting": function() {
                $( this ).dialog( "close" );
            },
            "Yes, I need help with this syntax error": function() {
                $( this ).dialog( "close" );
                $("#request-form").ajaxSubmit({
                    dataType: 'json',
                    data: {allow_syntax_error: true},
                    success: submit_handler
                })
            }
        },
        close: function( event, ui ) {
            $('.leader-line').each(function(){
                this.remove()
            })
        }

    })

    $('#processing').dialog({
        resizable: false,
        height: 50,
        // width: 150,
        modal: true,
        closeText: '',
        bgiframe: true,
        closeOnEscape: false,
        autoOpen: false,
    })

})