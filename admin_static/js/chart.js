$(function () {
          $.getJSON('http://localhost/test.php', function (data) {    
            $('#test1').highcharts({
                    chart: {
                    type: 'spline'
                },
                title: {
                    text: '最近7天的用户统计'
                },
                subtitle: {
                    text: '当日注册、当日登录、注册用户总数的线形图'
                },
                xAxis: {
                    type: 'datetime',
                    dateTimeLabelFormats: { // don't display the dummy year
                        month: '%e. %b',
                        year: '%b'
                    },
                    title: {
                        text: 'Date'
                    }
                },
                yAxis: {
                    title: {
                        text: '注册人数'
                    },
                    min: 0
                },
                tooltip: {
                    headerFormat: '<b>{series.name}</b><br>',
                    pointFormat: '{point.x:%e. %b}: {point.y:.2f}'
                },

                plotOptions: {
                    spline: {
                      marker: {
                          enabled: true
                      }
                  }
                },

                series: [{
                    name: '当日注册',
                    // Define the data points. All series have a dummy year
                    // of 1970/71 in order to be compared on the same x axis. Note
                    // that in JavaScript, months start at 0 for January, 1 for February etc.
                    data: data['a']
                }, {
                    name: '当日登录',
                    data: data['b'],
                    visible: false
                }, {
                    name: '注册用户总数',
                    data: data['c'],
                    visible: false
                }]
              });
          })   
      })