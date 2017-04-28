 //导入工具包require('node_modules里面对应的模块')
var gulp = require('gulp'),//本地安装gulp所用到的地方
	sass = require('gulp-sass'),//引入组件
	minifyCss = require('gulp-minify-css');
//	uglify = require('gulp-uglify')

//定义一个testSass任务，任务名称自己定义
gulp.task('testSass', function(){
	return gulp.src('sass/style.scss')//该任务针对的文件
			   .pipe(sass())//该任务调用的模块	
			   .pipe(gulp.dest('css'));//将会在css下生成style.css
});

//css压缩
gulp.task('minicss' ,['testSass'],function(){
	gulp.src('css/style.css') //要压缩的文件
		.pipe(minifyCss({
            advanced: false,//类型：Boolean 默认：true [是否开启高级优化（合并选择器等）]
            compatibility: 'ie7',//保留ie7及以下兼容写法 类型：String 默认：''or'*' [启用兼容模式； 'ie7'：IE7兼容模式，'ie8'：IE8兼容模式，'*'：IE9+兼容模式]
            keepBreaks: false,//类型：Boolean 默认：false [是否保留换行]
            keepSpecialComments: '*'
            //保留所有特殊前缀 当你用autoprefixer生成的浏览器前缀，如果不加这个参数，有可能将会删除你的部分前缀
        }))
		.pipe(gulp.dest('css/mincss'));
});

//JS压缩
/*gulp.task('minjs', function(){
	gulp.src(['js/*.js','!js/{common,slider}.js'])
		.pipe(uglify({
			//mangle: true,//类型：Boolean 默认：true 是否修改变量名
            mangle: {except: ['require' ,'exports' ,'module' ,'$']}//排除混淆关键字
        }))
		.pipe(gulp.dest('js/minjs'));
})*/
//监听
gulp.task('watch', function() {
    gulp.watch(['sass/**/*.scss'],['testSass']);
});

//默认任务
gulp.task('default',['watch','minicss']);
