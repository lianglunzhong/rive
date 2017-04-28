/*
function getUrlVar(key){
	var result = new RegExp(key + "=([^&]*)", "i").exec(window.location.search); 
	return result && unescape(result[1]) || ""; 
}

$(document).ready(function(){

    $("#id_category").change(function() {
        window.location.href = window.location.pathname + "?cid="+$(this).val();
    });
    
    var cid = getUrlVar('cid');
    if(cid){
        $("#id_category").val(cid);
    }
    */
/*
$("input[name^='ATTRIBUTE_']").change(function() {
    alert('hello');
});
});
*/
