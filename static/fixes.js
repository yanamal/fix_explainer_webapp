function highlight_nodes() {
    $('.ast-node').mouseover(function(e)
        {
            e.stopPropagation();
            const node_id = $(this).attr('data-node-id')

            $('.ast-node').removeClass('highlight'); // stop highlighting everything else

            $(`[data-node-id="${node_id}"]`).addClass('highlight');

            // $(this).connections({to: `[data-node-id="${node_id}"]`, class: 'mapping'})
        });

    $('.ast-node').mouseout(function(e)
        {
            const node_id = $(this).attr('data-node-id')
            $(`[data-node-id="${node_id}"]`).removeClass('highlight');
            // $('.mapping').connections('remove');
        });
}

function expand_trees(){
    child_nodes = $('.ast-node>.ast-node')  // nodes which are a child of some other node (non-root nodes)
    child_nodes.each(function(child_index){
        node_text = $( this ).text()
        let placeholder_span=$('<span/>', {class: 'placeholder'}).text(node_text)
        $( this ).after(placeholder_span)
        $( this ).prependTo(placeholder_span)
        $( this ).addClass('shifted-tree-node')

        let node_name_span=$('<span/>', {class: 'superscript'}).text($( this ).attr('data-node-name'))
        $( this ).prepend(node_name_span)


        $( this ).animate({top: "200px"}, 600,
            function() {
                placeholder_span.connections({to: `#${$(this).attr('id')}`})  //.html($( this ).attr('data-key'))
            })
    })
}

function apply_delete_style_to_text(selector) {
    // apply strikethrough styling to just the text inside the node itself (not child text)
    $(selector).contents().filter(function() {
        return this.nodeType == Node.TEXT_NODE
    }).each(function(){
        deleted_text_span = document.createElement('span')
        deleted_text_span.innerHTML=this.textContent
        deleted_text_span.className = "delete-text"
        this.parentNode.insertBefore(deleted_text_span, this)
        this.parentNode.removeChild(this);
    });
}

function add_insertion_placeholder(inserted_elem, insert_into) {
    target_parent_id = inserted_elem.getAttribute('data-insert-into')
    target_parent = $(`[data-node-id="${target_parent_id}"]`, insert_into)[0]

    target_before = null
    target_before_id = inserted_elem.getAttribute('data-insert-before')
    if(target_before_id){
        target_before = $(`[data-node-id="${target_before_id}"]`, insert_into)[0]
    }

    placeholder_span = document.createElement('span')
    placeholder_span.className = "insertion-placeholder"
    placeholder_span.id = `insert_${inserted_elem.id}`
    target_parent.insertBefore(placeholder_span, target_before)

    return placeholder_span
}

all_leader_lines = []

function apply_special_styling() {
    // Apply styling that can't be achieved through just CSS
    // but needs to be applied after the element is attached to the document

    $('.before-fix-code .move-node').each(function(node_i){
        // placeholder_span = add_insertion_placeholder(this)
        block = this.closest(".code-block")
        placeholder_span = $(`#insert_${this.id}`)[0]
        line = new LeaderLine(
            this,
            placeholder_span,
            {
                path: 'magnet',
                startSocket: 'top',
                endSocket: 'top',
                color: 'rgba(30, 130, 250, 0.5)',
                size: 2,
            }
          );
        //line.prependTo(block)
        console.log(line)
        all_leader_lines.push(line)
    })

    $('.insert-multiline-span').each(function(){
        insertion_symbol_span = $('<span/>', {class: 'insertion-multiline-indicator'}).html('&#8826;')
        this.prepend(insertion_symbol_span[0])
        insertion_symbol_span.css({
            left: `${-insertion_symbol_span.position().left-5}px`,
            top: `${-insertion_symbol_span.position().top-5}px`
        })
    })

    $('.insert-span').each(function(){
        insertion_symbol_span = $('<span/>', {class: 'insertion-inline-indicator'}).html('&#8911;')[0]
        this.parentNode.insertBefore(insertion_symbol_span, this)
        insertion_symbol_span.insertBefore(this, null)
    })

}

function wrap_text_in_spans(selection, span_class) {
    $('.ast-node', selection).contents().filter(function() {
        return this.nodeType == Node.TEXT_NODE
    }).each(function(){
        text_span = document.createElement('span')
        text_span.innerHTML=this.textContent
        text_span.className = span_class
        this.parentNode.insertBefore(text_span, this)
        this.parentNode.removeChild(this);
    })
}

function generate_inline_fix_html(source, dest, el_id) {
    // Get html of code to display
    let code_pre = $('<pre/>', {class: 'code-block before-fix-code'}).html(source)

    // Get html of dest code (to extract additional edit information)
    let dest_code_pre = $('<pre/>', {class: 'code-block after-fix-code'}).html(dest)

    let tab_contents = $('<div/>', {id: el_id})
    tab_contents.append(dest_code_pre)
    tab_contents.append(code_pre)

    // wrap each bit of text into its own span that's distinct from the spans that indicate AST structure
    // this makes it easier to compare and manipulate the text belonging to each node (which may be intermixed with child nodes)
    wrap_text_in_spans(code_pre, 'text-span')
    wrap_text_in_spans(dest_code_pre, 'text-span')



    // for each insert edit, inject the inserted code into the code being displayed, and mark it up as needed.

    // get top-level insertion nodes (don't visualize inserting each node one-by-one; insert whole subtrees together)
    $(':not([class*="insert-node"])>.insert-node', dest_code_pre).each(function(i){

        // make a copy of this subtree, which will be inserted into the visualization
        to_insert = this.cloneNode(deep=true)
        // remove any nodes in this subtree that aren't actually getting inserted
        // (e.g. when inserting a block "around" an existing bit of code, by inserting and then moving existing matching code in)
        $(to_insert).find('.ast-node:not([class*="insert-node"])').remove()

        // for each remaining child node, remove its own insert-node class, since it will be inserted *along with* the parent node.
        $(to_insert).find('.insert-node').removeClass('insert-node')

        // Grab any potential text we will need to insert alongside the actual AST node
        // One major example is when inserting an entire else close to an existing if,
        // the 'else' token itself is just some text that magically appears as part of the if node.
        text_node_before=null
        text_node_after=null
        if(this.previousSibling && this.previousSibling.classList.contains('text-span')) {
            text_node_before = this.previousSibling.cloneNode(deep=true)
        }
        if(this.nextSibling && this.nextSibling.classList.contains('text-span')) {
            text_node_after = this.nextSibling.cloneNode(deep=true)
        }

        // figure out where to insert
        parent_id = this.parentNode.getAttribute('data-node-id')
        next_sib_id = $(this).nextAll('.ast-node:first').attr('data-node-id') // may be undefined, if this is the last node in the parent

        insertion_parent = code_pre.find(`[data-node-id="${parent_id}"]`)

        // Find the element that would be before the insertion spot, to check whether it is a text-span
        elem_before_insertion = insertion_parent.children().last()
        next_sib = undefined // also find actual sibling to insert before
        if(next_sib_id){
            next_sib = insertion_parent.find(`[data-node-id="${next_sib_id}"]`)[0]
            elem_before_insertion = $(next_sib).prev() // TODO: fix names or types - next_sib is element, elem_before_insertion is jquery object
        }

        if(elem_before_insertion.hasClass('text-span')){
            // There is some text in the place where we are inserting the node.
            // See if it matches either of the bits of text to insert (and change behavior if it does)
            existing_text = elem_before_insertion.text()
            if(text_node_after && text_node_after.textContent == existing_text) {
                // the existing text node matches the text that goes after the inserted node. insert before existing text
                next_sib = elem_before_insertion[0]
                // also, don't bother inserting a second copy of that text
                text_node_after = null
            }
            else if(text_node_before && text_node_before.textContent == existing_text) {
                // don't bother inserting a second copy of the text before the insertion node
                text_node_before = null
            }
        }

        // finally, put together and insert everything that needs to be inserted
        insert_span = $('<span/>', {class: 'insert-span'})
        for(elem of [text_node_before, to_insert, text_node_after]){
            insert_span.append(elem)
        }
        if(insert_span.text().includes('\n')) {
            insert_span.attr('class','insert-multiline-span')
        }

        insertion_parent[0].insertBefore(insert_span[0], next_sib)
    })

    // for each move edit, figure out where it should be moved and add the metadata
    $('.move-node', code_pre).each(function(i){
        node_id = this.getAttribute('data-node-id')
        mapped_node = $(`[data-node-id="${node_id}"]`, dest_code_pre)

        parent_id = mapped_node.parent().attr('data-node-id')
        this.setAttribute('data-insert-into', parent_id)

        next_sib_id = mapped_node.nextAll('.ast-node:first').attr('data-node-id')
        if(next_sib_id) {
            this.setAttribute('data-insert-before', next_sib_id)
        }

        add_insertion_placeholder(this, code_pre)

    })

    // for each rename edit, get the replacement text
    $('.rename-node', code_pre).each(function(i){
        node_id = this.getAttribute('data-node-id')
        mapped_node_text = $(`[data-node-id="${node_id}"]>.text-span`, dest_code_pre).text()

        replacement_span = $('<span/>', {class: 'replacement'}).text(mapped_node_text)
        this.prepend(replacement_span[0])

    })

    // deletions will get formatted correctly through CSS (strikethrough)

    // return finished object for adding to the document
    return tab_contents
}

function load_sequence_data(data_source) {
    // reset:
    $('#code-div').html('<ul id="tab-titles"></ul>')
    for(line of all_leader_lines) {
        line.remove()
    }
    all_leader_lines = []
    // regenerate:
    step_i = 1
    for (step_data of data_source) {
        el_id = `fix-${step_i}`
        tab_title = `Fix ${step_i}`
        fix_html = generate_inline_fix_html(step_data['source'], step_data['dest'], el_id)
        $('#code-div').append(fix_html)
        $('#tab-titles').append($(`<li><a href="#${el_id}">${tab_title}</a></li>`))

        //$(fix_html).prepend(step_data['dest'])  //TODO: position:absolute;visibility: hidden;

        step_i += 1
    }

    $( "#code-div" ).tabs({
        activate: function( event, ui ) {
            for(line of all_leader_lines) {
                line.position()
            }
        }
    });
}

function animate_fix(){
    // first, hide all arrows - they often look nonsensical during the animation
    $('.leader-line').css('visibility', 'hidden')

    // find current element
    fix_elem = $('#code-div').tabs().data().uiTabs.panels[$('#code-div').tabs('option', 'active')]

    nodes_to_move = [] // list of node to animate moving
    // first, decide which nodes to move and which to fade out.
    // instantly move nodes that need to be moved, in order to have them in the correct position when calculating moves for child nodes later in this same loop.
    $('.before-fix-code .ast-node', fix_elem).each(function(i){
        node_id = this.getAttribute('data-node-id')

        fixed_node = $(`.after-fix-code [data-node-id=${node_id}]`, fix_elem)
        // TODO: also skip movement/animate fade out for rename nodes
        if(fixed_node.length > 0) {
            my_offset = $(this).offset()
            fixed_offset = fixed_node.offset()
            top_move = fixed_offset.top-my_offset.top
            left_move = fixed_offset.left-my_offset.left
            // only bother with move logic if it actually needs moving.
            if (top_move != 0 || left_move != 0){
                $(this).css({
                    'top': top_move,
                    'left': left_move
                })
                nodes_to_move.push({
                    'node': this,
                    'top': top_move,
                    'left': left_move
                })
            }
        }
        else
        {
            // TODO - fade out
        }
    })

    // actually animate movement
    // TODO: do something with the arrows?
    for(move_obj of nodes_to_move){
        // move back to original position
        $(move_obj.node).css({
            'top': 0,
            'left': 0
        })
        $(move_obj.node).animate({
            'top': move_obj.top,
            'left': move_obj.left
        })
    }

    // animate fade out of deleted text spans
    $('.before-fix-code .delete-node>.text-span', fix_elem).each(function(i){
        $(this).animate({
            'opacity': 0
        })

    })

    // animate fade out & move in replacement for rename nodes
    $('.before-fix-code .rename-node>.text-span', fix_elem).each(function(i){
        $(this).animate({
            'opacity': 0
        })

    })
    $('.before-fix-code .rename-node>.replacement', fix_elem).each(function(i){
        $(this).animate({
            'top': -6 // dunno, position:absolute nonsense.
        })

    })

    $(":animated").promise().done(function() {
        $('.after-fix-code', fix_elem).animate({
            opacity: 1
        })
        $('.before-fix-code', fix_elem).animate({
            opacity: 0
        })
        $(":animated").promise().done(function() {
            reset_animation(fix_elem)
            $( "#code-div" ).tabs( "option", "active", $("#code-div").tabs('option', 'active')+1 );
        })
    });
}

function reset_animation(elem){
    $('span:not(.insertion-multiline-indicator)', elem).attr('style','');
    $('.leader-line').attr('style','');
    $('.code-block', fix_elem).attr('style','');
}