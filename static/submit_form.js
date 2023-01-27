
function add_unit_test(){
    $('#test_fields').append('<textarea name="test[]" rows="1" cols="50"></textarea>')
}

function remove_unit_test(){
    $('textarea[name="test[]"]').last().remove()
}

function add_correct_version(){
    $('#correct_fields').append('<textarea type="textarea" rows="4" cols="50" name="correct[]"></textarea>')
}

function remove_correct_version(){
    $('textarea[name="correct[]"]').last().remove()
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