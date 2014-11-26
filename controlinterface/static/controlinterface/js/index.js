// Add some initial configuration data. Each widget's `metric` or `metrics`
// will contain data once the corresponding ajax request has been made.
var data = {
  url: '/api/v1/controlinterface/metric/',
  token: 'dashboards:dashboards',
  step: 10000,
  widgets: {
    all: {
      from: '-1d',
      interval: '1h',
      nulls: 'omit',
      type: 'lines',
      title: 'Unique Users (last 24 hours)',
      metrics: [{
        title: 'Clinic',
        key: 'stores.ndoh_prd_live.prd.clinic.sum.unique_users.last'
      }, {
        title: 'Personal',
        key: 'stores.ndoh_prd_live.prd.personal.sum.unique_users.last',
      }, {
        title: 'CHW',
        key: 'stores.ndoh_prd_live.prd.chw.sum.unique_users.last',
      }],
    },
    a: {
      title: 'Unique Clinic Users (last 30 days)',
      key: 'stores.ndoh_prd_live.prd.clinic.sum.unique_users.last',
      from: '-30d',
      interval: '1d',
      nulls: 'omit',
      type: 'last'
    },
    b: {
      title: 'Unique Personal Users (last 30 days)',
      key: 'stores.ndoh_prd_live.prd.personal.sum.unique_users.last',
      from: '-30d',
      interval: '1d',
      nulls: 'omit',
      type: 'last'
    },
    c: {
      title: 'Unique CHW Users (last 30 days)',
      from: '-30d',
      interval: '1d',
      nulls: 'omit',
      key: 'stores.ndoh_prd_live.prd.chw.sum.unique_users.last',
      type: 'last'
    }
  }
};


  // Create the widget components. Widget configuration would be done here.
  var last = sapphire.widgets.last();
  var lines = sapphire.widgets.lines();


  // Update the dashboard on page load, then every `data.step` milliseconds.
  update();
  setInterval(update, data.step);


  // Select each widget element by id, then draw it using the sapphire components
  // we created above
  function draw() {
    d3.select('#a')
      .datum(data.widgets.a)
      .call(last);

    d3.select('#b')
      .datum(data.widgets.b)
      .call(last);

    d3.select('#c')
      .datum(data.widgets.c)
      .call(last);

    d3.select('#all')
      .datum(data.widgets.all)
      .call(lines);
  }


  // Updates each widget's metrics one by one, then draws the dashboard.
  function update() {
    var i = -1;
    var widgets = d3.values(data.widgets);

    function next() {
      if (++i < widgets.length) updateWidget(widgets[i], next);
      else draw();
    }

    next();
  }


  // Update a single widget's values by making an ajax request, then invokes a
  // callback when done.
  //
  // 1. Create the request object as a json request to the configured url, with
  // the from and interval parameters relevant to the widget and the auth token
  // associated with the vumi-go account.
  //
  // 2. Add each of the widget's metrics to the query
  //
  // 3. Make the request
  //
  // 4. Update the widget's metrics with the response
  //
  // 5. Invoke the `done` callback so the next metric request or draw can happen
  function updateWidget(widget, done) {
    var req = superagent
      .get(data.url)
      .set('Authorization', ['ApiKey', data.token].join(' '))
      .type('json')
      .query({
        from: widget.from,
        interval: widget.interval,
        nulls: widget.nulls
      });

    metrics(widget)
      .forEach(function(d) { req.query({m: d.key}); });

    req
      .end(function(res) {
        if (!res.ok) {
          console.error(res.text);
          return;
        }
        // We need to stick the response into the expected format
        results = {};
        res.body.objects
          .forEach(function(met) {
            results[met.key] = met.values;
          });
        updateMetrics(widget, results);
        done();
      });
  }


  // Updates a widget's metric values using the given api response data.
  function updateMetrics(widget, data) {
    metrics(widget)
      .forEach(function(d) {
        d.values = data[d.key];
      });
  }


  // Accesses a widget's metric data.
  //
  // `last` widgets only have a single metric. This function simplifies things
  // by allowing us to treat all widgets as having multiple widgets.
  //
  // Note that the `last` widget could have also been configured to handle this
  // distinction. Using this approach instead just means less widget
  // configuration is needed.
  function metrics(widget) {
    return widget.metrics
      ? widget.metrics
      : [widget];
  }
