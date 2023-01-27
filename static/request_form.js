$( document ).ready(function() {
    for(problem in homework_1){
        $('#problem-select').append($('<option/>', {value: problem}).text(problem))
    }
    $("#problem-select").prop("selectedIndex", -1);
});

function ajax_submit(){
    let form = new FormData(document.forms.fix_form)
    console.log('sending request')
    $.ajax({
        type: "POST",
        url: "/generate",
        data: JSON.stringify({
            'code': form.get('code'),
            'correct': homework_1[form.get('problem')]['solutions'],
            'tests': homework_1[form.get('problem')]['tests']
        }),
        contentType: "application/json",
        dataType: 'json',
        success: function(result) {
            console.log(result);
            $( "#code-div" ).tabs( "destroy" ); // TODO: move back to loading logic, make sure tabs exist first somehow
            load_sequence_data(result)
            // TODO: are the following necessary?
            highlight_nodes()
            apply_special_styling()
        }
    });
}
