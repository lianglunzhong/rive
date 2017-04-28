// --------------------------------------------------
// common
// --------------------------------------------------

$(function() {
    $('.change a').click(function() {
        $('#change_password').fadeToggle();
    });
})
$(function() {
    $(".nav-pills li").click(function() {
        $(this).addClass('active').siblings().removeClass('active');
    });
})
$(function() {
    $(".allCheck").click(function() {
        if (this.checked) {
            $("#checkList :checkbox").prop("checked", true);
        } else {
            $("#checkList :checkbox").prop("checked", false);
        }
        var checkVal = [];
        var ch = [1, 2, 3]
        $("#checkList :checkbox[checked]").each(function(i) {
            checkVal[i] = $(this).val();
        })
    });
})


$(function() {
    var qty = $('.minus').siblings('.JS-qty')
    $(".plus").click(function() {
        var num = parseInt(qty.val()) || 0;
        qty.val(num + 1);
    });
    //减去
    $(".minus").click(function() {
        var num = parseInt(qty.val()) || 0;
        num = num - 1;
        num = num < 1 ? 1 : num;
        qty.val(num);
    });
    qty.keypress(function(b) {
        var keyCode = b.keyCode ? b.keyCode : b.charCode;
        if (keyCode != 0 && (keyCode < 48 || keyCode > 57) && keyCode != 8 && keyCode != 37 && keyCode != 39) {
            return false;
        } else {
            return true;
        }
    }).keyup(function(e) {
        var keyCode = e.keyCode ? e.keyCode : e.charCode;
        if (keyCode != 8) {
            var numVal = parseInt(qty.val()) || 0;
            numVal = numVal < 1 ? 1 : numVal;
            qty.val(numVal);
        }
    }).blur(function() {
        var numVal = parseInt(qty.val()) || 0;
        numVal = numVal < 1 ? 1 : numVal;
        qty.val(numVal);
    });
});

//添加
function plus(product_id) {
    var qty = $("#product_" + product_id).val();
    var num = parseInt(qty) || 0;
    num += 1;
    $("#product_" + product_id).val(num);
}

//减去
function minus(product_id) {
    var qty = $("#product_" + product_id).val();
    var num = parseInt(qty) || 0;
    num -= 1;
    num = num < 1 ? 1 : num;
    $("#product_" + product_id).val(num);
}