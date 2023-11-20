event_cache = []  //list of logged events (that have not been sent over to the server yet)

function get_attrs(el) {
    attrs = {}
    for (a of el.attributes) {
        if(a.specified) {
            attrs[a.name]=a.value
        }
    }
    return attrs
}

// add logging for clicks on certain elements
function log_clicks(selector) {
    console.log($(selector))
    $(selector).on('mouseup', function (e){
        e.stopPropagation(); // prevent parent elements from logging this event

        event_cache.push({
            timestamp: new Date().getTime(),
            event_type: 'click',
            selector: selector,
            id: e.target.id,
            attributes: get_attrs(e.target),
            page_data: page_data
        })

        console.log(event_cache.slice(-1)[0])
        // console.log(JSON.stringify(event_cache.slice(-1)[0]))
    })
}


// add logging for hovers on certain elements
const hover_threshold = 100  // ms
function log_hovers(selector) {
    console.log($(selector))
    $(selector).mouseover(function(e){
        e.stopPropagation();
        //console.log(e.target)
        //console.log(this)

        $(this).data('hover_start', new Date().getTime())
    })
    $(selector).mouseout(function(e){
        e.stopPropagation();
        const duration = ( new Date().getTime() - $(this).data('hover_start') )
        if(duration >= hover_threshold) {
            event_cache.push({
                timestamp: new Date().getTime(),
                event_type: 'hover',
                selector: selector,
                id: this.id,
                attributes: get_attrs(this),
                duration: duration,
                page_data: page_data
            })

            console.log(event_cache.slice(-1)[0])
        }
    })
}


// log custom event (e.g. value change)
function log_custom_event(event_type, event_data) {
    event_cache.push({
        timestamp: new Date().getTime(),
        event_type: event_type,
        data: event_data,
        page_data: page_data
    })

    console.log(event_cache.slice(-1)[0])
}


// send event logs to server (and empty cache)
function send_logs(){
    $.ajax({
    type: "POST",
    url: "/log_interactions",
    data: JSON.stringify(event_cache),
    contentType: "application/json",
    dataType: 'json',
    success: function(result) {
        console.log(result);
        event_cache = []
    }
    })
}

function send_logs2(){
    // TODO: debug
    navigator.sendBeacon("/log_interactions", JSON.stringify(event_cache));
}
