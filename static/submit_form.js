
function add_unit_test(contents="helloWorld() == 'Hello World!'"){
    let num_existing = $('#test_fields .test_field').length
    let test_id = `test_${num_existing+1}`
    let ace_id = `ace_${test_id}`
    let form_id = `form_${test_id}`
    test_html = `<div id=${test_id} class="test_field">
    <div id="${ace_id}"></div>
    <textarea id="${form_id}" type="textarea" name="test[]" rows="1" cols="50" style="display:none;"></textarea>
    </div>
    `
    console.log(test_html)
    $('#test_fields').append(test_html)
    let editor = ace.edit(ace_id, {
        maxLines:1,
        minLines:1
    })

    editor.setTheme("ace/theme/dawn");
    editor.session.setMode("ace/mode/python");
    editor.getSession().on("change", function () {
        $(`#${form_id}`).val(editor.getSession().getValue());
    });
    editor.setValue(contents)
    editor.clearSelection()

    editor.on('blur', function(){
        console.log('ace blur '+ace_id)
        validate_ace_field(ace_id)
    })
}

function remove_unit_test(){
    $('#test_fields .test_field').last().remove()
}

// TODO: correctly add ace to prefilled version. prefill using JS?.. same with unit tests
function add_correct_version(contents=`def helloWorld():
  return 'Hello World!'`){
    let num_existing = $('#correct_fields .correct_field').length
    let sol_id = `sol_${num_existing+1}`
    let ace_id = `ace_${sol_id}`
    let form_id = `form_${sol_id}`
    $('#correct_fields').append(`<div id=${sol_id} class="correct_field">
    <div id="${ace_id}"></div>
    <textarea id="${form_id}" type="textarea" rows="10" cols="70" name="correct[]" style="display:none;"></textarea>
    </div>
    `)
    let editor = ace.edit(ace_id, {
        maxLines:10,
        minLines:10
    })
    editor.setTheme("ace/theme/dawn");
    editor.session.setMode("ace/mode/python");
    editor.getSession().on("change", function () {
        $(`#${form_id}`).val(editor.getSession().getValue());
    });
    editor.setValue(contents)
    editor.clearSelection()

    editor.on('blur', function(){
        console.log('ace blur '+ace_id)
        validate_ace_field(ace_id)
    })
}

function remove_correct_version(){
    $('#correct_fields .correct_field').last().remove()
}


function add_practice_activity(page="", exercise="", desc=""){
    $('#practice_fields').append(`<div class='practice_box'>
                    <label>Runestone URL of book sub-chapter: </label>
                    <input type="text" size="50" name="page_url[]" value="${page}"><br/>
                    <label>Activity ID: </label>
                    <input type="text"  size="50" name="exercise_name[]" value="${exercise}"><br/>
                    <label>Short description of issue that this activity may help with: </label>
                    <input type="text"  size="100" name="issue_desc[]" value="${desc}">
                </div>`)
}

function remove_practice_activity(){
    $('.practice_box').last().remove()
}

function validate_ace_field(ace_id){
    let editor = ace.edit(ace_id)
    let code = editor.getSession().getValue()
    console.log(code)
    $.ajax({
        type: "POST",
        url: "/validate_compile",
        data: JSON.stringify({
            'code': code,
        }),
        contentType: "application/json",
        dataType: 'json',
        success: function(result) {
            console.log(result);
            if(result['compiles']) {
                editor.session.setAnnotations([]) // reset to blank
                //return true
            }
            else {
                editor.session.setAnnotations([{
                    row: result['lineno']-1,
                    column: result['offset']-1, // TODO: somehow actually use offset?.. just stick it in the text?..
                    text: result['error'],
                    type: 'error'
                }])
                //return false
            }

        }
    })
}

// TODO: this won't work because I have to do ajax calls inside validation.
// disable submit unless all fields are validated since last edit?..
function validate_and_submit() {
    $('.ace_editor').each(function(){
        let ace_id=$(this).attr('id')
        if(!validate_ace_field(ace_id)){
            return false  // TODO: validate all of them? put up a notification?
        }
    })
    return true
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

$( document ).ready(function() {
    // load one blank correct solution (unless prefilled)
    if($('#correct_fields textarea').length === 0) {
        add_correct_version()
    }

    // load one blank unit test (unless prefilled)
    if($('#test_fields textarea').length === 0) {
        add_unit_test()
    }

    $('#correct_fields textarea').each(function(){
        field_id = console.log(this.id);
        // ace.edit(field_id)
    })
});