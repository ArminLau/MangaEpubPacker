function uploadImage(inputFile){
    var id = $(inputFile).prop("id");
    let url = null;
    let fileObj = document.getElementById(id).files[0];
    if (window.createObjcectURL != undefined) {
        url = window.createOjcectURL(fileObj);
    } else if (window.URL != undefined) {
        url = window.URL.createObjectURL(fileObj);
    } else if (window.webkitURL != undefined) {
        url = window.webkitURL.createObjectURL(fileObj);
    }
    $("#display").prop("src",url);
    var array = $(inputFile).val().split("\\");
    array = array[array.length-1].toString().split(".");
    $("input[name="+id+"]").val(array[array.length-2]);
    $(inputFile).parent().parent().parent().attr("link", url);
}

function appendTocItem() {
    var template = "<div class=\"list-group-item list-group-item-action\" link=\"default\">\n" +
        "                            <div class=\"d-flex w-100 justify-content-between\">\n" +
        "                                <h4 class=\"mb-1\">${toc-title}</h4>\n" +
        "                                <span class=\"badge\">\n" +
        "                                    <input type=\"file\" accept=\".png, .jpg, .jpeg\" id=\"toc-id\" onchange=\"uploadImage(this)\"/>\n" +
        "                                    <input type=\"text\" name=\"toc-id\" style=\"display: none\"/>\n" +
        "                                    <label class=\"btn btn-danger btn-no-margin\" onclick=\"deleteTocItem(this)\">删除</label>\n" +
        "                                    <label class=\"btn btn-success btn-no-margin\" for=\"toc-id\">选择图片</label>\n" +
        "                                </span>\n" +
        "                            </div>\n" +
        "                        </div>";
    var toc_title = $("#new-toc-title").val();
    if(toc_title.toString().length < 1){
        return;
    }
    var reg = new RegExp("toc-id", "g");
    $("#toc-items").append(template.replace(reg, "file-"+getNextFileId()).replace("${toc-title}", toc_title));
}
function deleteTocItem(obj) {
    $(obj).parent().parent().parent().remove();
}
function getNextFileId() {
    var id = $("#toc-items").children(":last-child").find("input").attr("id").toString();
    if(id.indexOf("-") == -1){
        return 0;
    }else {
        return parseInt(id.split("-")[1])+1;
    }
}
$("#toc-items").on('click', '.list-group-item', function () {
    var link = $(this).attr("link");
    link = link == "default" ? "/static/image/image-frame.svg" : link;
    $("#display").prop("src", link);
});
$("#form").submit(function (event) {
    event.preventDefault();
    return false;
});
function showMsg(msg, delay){
    var target = $("#tip");
    if(target.length==0){
        var template = '<div class="w-100 alert alert-warning alert-dismissible fade show" role="alert" id="tip" style="display: none"><div></div><button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>';
        $("#tip-container").html(template);
        target = $("#tip");
    }
    $(target).children("div").html(msg);
    $(target).fadeIn();
    if(delay != null){
    setTimeout(function () {
        $("#tip").fadeOut();
    }, delay);
   }
}
$("#pack").click(function () {
    var path = $("input[name='path']").val();
    var targetPath = $("input[name='targetPath']").val();
    if(targetPath.length < 1){
        targetPath = path;
    }
    var title = $("input[name='title']").val();
    var bulkMode = $("#bulkMode").prop("checked");
    var overwrite = $("#overwriteFile").prop("checked");
    if(path.length < 1 || (title.length < 1 & bulkMode == false)){
        showMsg("表单必填项没有填写，请补充好后再重试!", 3000);
        return;
    }
    var postData = null;
    if(bulkMode){
        postData = handleBulkPack(path, targetPath);
    }else {
        postData = handleSinglePack(path, targetPath);
    }
    postData["overwrite"] = overwrite;
    //alert(JSON.stringify(postData));
    $("#waiting").css("visibility","visible");
    $.ajax({
        url:"/pack",
        type:"POST",
        data:JSON.stringify(postData),
        contentType:"application/json",  //缺失会出现URL编码，无法转成json对象
        success:function(result){
            $("#waiting").css("visibility","hidden");
            var data = jQuery.parseJSON(result)
            showMsg(data.msg);
            if(data.status == 1){
                $("#toc-items").find(".list-group-item").attr("link", "default");
                $("#display").prop("src","/static/image/image-frame.svg");
                clearCustomToc(); //清除目录的自定义选项
                if($("#autoClear").prop("checked")){
                    $("input[name]").val(""); //成功生成epub文件后自动清空表单
                }
            }
        }
    });
});
function clearCustomToc(){
    var default_filter = "cover_toc_bodymatter_colophon";
    $("#toc-items").find(".list-group-item").each(function (index, element) {
        if(default_filter.indexOf($(element).find("input[name]").attr("name")) == -1){
            $(element).remove();
        }
    });
}
function handleBulkPack(path, targetPath) {
    var postData = {};
    postData["bulk"] = true;
    postData["path"] = path;
    postData["targetPath"] = targetPath;
    return postData;
}
function handleSinglePack(path, targetPath) {
    var postData =  {};
    postData["bulk"] = false;
    postData["path"] = path;
    postData["targetPath"] = targetPath;
    var description = $("textarea[name='description']").val();
    var baseInfoFlag = "meta_info";
    var tocInfoFlag = "toc_info";
    var baseInfo = {}
    baseInfo["description"] = description;
    $("#baseInfo").find("input[name]").each(function (index, element) {
        baseInfo[$(element).prop("name")] = $(element).val();
    });
    var tocInfo = {}
    $("#toc-items").find("input[name]").each(function (index, element) {
        var type = $(element).prop("name");
        var title = $(element).parent().parent().children("h4").text();
        var key = $(element).val();
        var temp = {}
        temp["title"] = title;
        temp["type"] = type;
        tocInfo[key] = temp;
    });
    postData[baseInfoFlag] = baseInfo;
    postData[tocInfoFlag] = tocInfo;
    return postData;
}

