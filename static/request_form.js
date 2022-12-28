function ajax_submit(){
    let form = new FormData(document.forms.fix_form)
    $.ajax({
        type: "POST",
        url: "/generate",
        data: JSON.stringify({
            'code': form.get('code'),
            'correct': form.getAll('correct[]'),
            'tests': form.getAll('test[]')
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

function add_unit_test(){
    $('#test_fields').append('<input type="text" name="test[]">')
}

function remove_unit_test(){
    $('input[name="test[]"]').last().remove()
}

function add_correct_version(){
    $('#correct_fields').append('<textarea type="textarea" rows="4" cols="50" name="correct[]"></textarea>')
}

function remove_correct_version(){
    $('textarea[name="correct[]"]').last().remove()
}