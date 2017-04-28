$(function(){
     $('input[name=conditions],input[name=restrictions]').click(function(){
            var $input = $('input[name=' + $(this).val() + ']');
            console.log($input)
            if($input.length){
                    $(this).parent().siblings().children().eq(4).attr('disabled','disabled');
                    $input.removeAttr('disabled')
            }else {
                    $(this).siblings('input[type=text]').attr('disabled','disabled');
            }
    });

    $('input[name=discount_method]').click(function(){
        var $input = $('input[name=' + $(this).val() + ']');
        if($input.length){
                $(this).siblings('input[type=text]').attr('disabled','disabled');
                $input.removeAttr('disabled')
        }else {
                $(this).siblings('input[type=text]').attr('disabled','disabled');
        }
    });

    $('input[name=promotion_method]').click(function(){
            var $this = $(this)
            val = $this.val();
            console.log(val)
            var c = $this.parent().siblings().find("input[name!=promotion_method]")
            c.attr('disabled','disabled');

            if(val == 'discount') {
            }else if(val == 'largess'){
                $this.siblings().removeAttr('disabled')
            }else if(val == 'freeshipping') {
            }else if(val == 'restrict') {
            }else if(val == 'secondhalf') {
            }else if(val == 'bundle') {
                $this.siblings().removeAttr('disabled')          
            }

            $("input[type=radio]").removeAttr('disabled')
            $("input[name=celebrity_avoid]").removeAttr('disabled')
    });

    $('#add_largess').click(function(){
            if( ! $('#pmethod_2').is(':checked')){
                    return false;
            }
            var $this = $(this),count = parseInt($this.attr('count')) + 1;
            var $div = $('<div class="form_item_content largess">\
                                            <label for="largess_SKU_' + count + '">SKU: </label><input name="largess[SKU][]" id="largess_SKU_' + count + '" class="inline short "/> &nbsp;&nbsp;&nbsp;&nbsp;\
                                            <label for="largess_price_' + count + '">价格: </label><input name="largess[price][]" id="largess_price_' + count + '" class="inline numeric" value="0"/> &nbsp;&nbsp;&nbsp;&nbsp;\
                                            <label for="largess_quantity_' + count + '">最大数量: </label><input name="largess[quantity][]" id="largess_quantity_' + count + '" class="inline numeric" value="1"/>&nbsp;&nbsp;<a href="#" class="delete_largess">删除本赠品</a>\
                                    </div>');
            $div.insertAfter($this.parent().parent().find('div:last'));
            $this.attr('count',count);
            return false;
    });
    
/*    $('.delete_largess').live('click',function(){
            if( ! $('#pmethod_2').is(':checked')){
                    return false;
            }
            $(this).parent().remove();
            return false;
    });*/

    //$(".datepick").datepicker().datepicker('option',{showAnim:'',dateFormat:'yy-mm-dd'});
});
