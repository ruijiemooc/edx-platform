;(function (define, undefined) {
    'use strict';
    define(['gettext', 'jquery', 'underscore', 'backbone', 'moment',
            'text!templates/student_profile/share_modal.underscore'],
        function (gettext, $, _, Backbone, Moment, badgeModalTemplate) {

            var ShareModalView = Backbone.View.extend({
                attributes: {
                    'class': 'badge-display'
                },
                events: {
                    'click .badges-modal': function (event) {event.stopPropagation();},
                    'click .badges-modal .close': 'close',
                    'click .badges-overlay': 'close'
                },
                close: function () {
                    this.$el.fadeOut('short', 'swing', _.bind(this.remove, this));
                },
                render: function () {
                    this.$el.html(_.template(badgeModalTemplate, this.model.toJSON()));
                    return this;
                }
            });

            return ShareModalView;
        });
}).call(this, define || RequireJS.define);
