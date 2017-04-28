$(function(){
	$('.no_limit_stock').bind('click',function(){
	    alert('1111');
	    if(stock == 0)
	    {
	        $('#product_stock').show();
	        $('#stock').val(-1);
	    }
	    if(stock == 1)
	    {
	        $('#product_stock').hide();
	        $('#stock').val(-99);
	    }
	});

	// $('#order_form').submit(function(e){
	// 	var psku = $('.psku');
	// 	for(var i =0 ;i<psku.length;i++){
	// 		if(psku[i].val() == ''){
	// 			psku[i].css('border-color', 'red')
	// 			e.preventDefault();
	// 		}
	// 	}
		
	// })
	$('.add-row').find('a').click(function(e){
		var click = $(this).attr('click') == undefined ? 0 : $(this).attr('click');
		// if($(this).html()=='Please save current package and then add another'){
		if($(this).html()=='Add another Package'){
			if(click == 0) {
				// $(this).replaceWith('<span>'+$(this).html()+'</span>');
				$(this).replaceWith('<span>Please save the current package information first, then create a new one.</span>')
			}else{
				$(this).attr('click', click*1+1);
			}
		}
	})
})
//订单详情页产品价格修改按钮
function change_price(product_id){
	$('#original_price'+product_id).hide();
	$('#change_price'+product_id).show();
}

function price_save(order_id,orderitem_id,product_id){
	var price = $("#change_price_input"+product_id).val();
	if(price){
		$('#price_save_'+product_id).attr('href','/orders/change_price_save/'+order_id+'/'+orderitem_id+'/'+product_id+'/'+price);
		return true;
	}else{
		alert('Please input price !')
	}
}
//订单详情页产品价格修改输入及数据提交保存
/*function change_price_input(price,order_id,orderitem_id,product_id){
	var a = $('#change_price'+product_id).has('a');
	if (!a.length>0){
		$('#change_price'+product_id).append("<a id='save_a' href='/orders/change_price_save/"+order_id+"/"+orderitem_id+"/"+product_id+"/"+price+"'>Save</a>");
	}else{
		$('#save_a').attr('href','/orders/change_price_save/'+order_id+'/'+orderitem_id+'/'+product_id+'/'+price);
	}
}*/

//订单详情页添加shipping_item里面的产品按钮
function add_anthor(package_id){
	$('#add_anthor_btn'+package_id).hide();
	$('#add_anthor_input'+package_id).show();
}

//订单详情页添加shipping_item里面的产品时的删除按钮
function ship_delete(package_id){
	$("#ship_sku"+package_id).val("");
	$("#ship_qty"+package_id).val("");
	$("#add_anthor_input"+package_id).hide();
	$("#add_anthor_btn"+package_id).show();
}


//订单详情页添加shipping_item里面的产品时的save按钮
function ship_save(order_id,package_id){
	var sku = $("#ship_sku"+package_id).val();
	var qty = $("#ship_qty"+package_id).val();
	if(order_id && package_id && sku && qty){
		$("#ship_save"+package_id).attr('href','/orders/shipitem_add_save/'+order_id+'/'+package_id+'/'+qty+'/'+sku);
		return true;
	}else{
		alert('Please enter the correct sku and qty !');
	}
}

function add_new(package_id){
	var onkeyup = String("this.value=this.value.replace(/\\D/g,'')");
	var onafterpaste = String("this.value=this.value.replace(/\\D/g,'')");
	var input_contron = String("onkeyup=")+onkeyup+String("  ")+String("onafterpaste=")+onafterpaste;
	console.log(input_contron);
	$("#sku_qty"+package_id).append("<br><br><div style='float:left;'><label for='sku'>Ref. :</label><input class='psku' type='text' name='"+package_id+"sku[]'></div><div style='float:left;padding-left:20px;'> <label for='qty'>Qty :</label><input  type='text' name='"+package_id+"qty[]'"+input_contron+"></div>");
}

//折扣输入控制
function discount_change(obj){
	var discount = obj.value;
	if(discount>1 || discount <=0){
		alert('Discount should be: 0 < discount <= 1');
		$("#new_discount").val('1.0');
	}
}

