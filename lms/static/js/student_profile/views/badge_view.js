;(function (define, undefined) {
    'use strict';
    define(['gettext', 'jquery', 'underscore', 'backbone', 'moment',
            'text!templates/student_profile/badge.underscore', 'js/student_profile/models/share_modal_model',
            'js/student_profile/views/share_modal_view'],
        function (gettext, $, _, Backbone, Moment, badgeTemplate, ShareModalModel, ShareModalView) {

            var BadgeView = Backbone.View.extend({
                initialize: function(options) {
                    this.context = _.extend(this.options.model.toJSON(), {
                        'created': new Moment(this.options.model.toJSON().created),
                        'ownProfile': options.ownProfile
                    });
                    this.badgeMeta = options.badgeMeta;
                },
                attributes: {
                    'class': 'badge-display'
                },
                events: {
                    'click .share-button-container': 'createModal'
                },
                createModal: function() {
                    var context = {};
                    _.extend(context, this.context);
                    _.extend(context, this.badgeMeta);
                    var modal = new ShareModalView({model: new ShareModalModel(context)});
                    modal.$el.hide();
                    modal.render();
                    $('body').append(modal.$el);
                    modal.$el.fadeIn();
                },
                render: function () {
                    this.$el.html(_.template(badgeTemplate, this.context));
                    return this;
                }
            });

            return BadgeView;
        });
}).call(this, define || RequireJS.define);
