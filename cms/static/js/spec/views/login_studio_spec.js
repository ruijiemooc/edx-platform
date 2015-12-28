define(['jquery', 'js/factories/login', 'common/js/spec_helpers/ajax_helpers', 'common/js/components/utils/view_utils'],
function($, LoginFactory, AjaxHelpers, ViewUtils) {
    'use strict';
    describe("Studio Login Page", function() {
        var submit_button;

        beforeEach(function() {
            loadFixtures('mock/login.underscore');
            /*jshint unused: false*/
            var login_factory = new LoginFactory("/home/");
            submit_button = $('#submit');
        });

        it('disable the submit button once it is clicked', function() {
            spyOn(ViewUtils, 'redirect').andCallFake(function(){});
            var requests = AjaxHelpers.requests(this);
            expect(submit_button).not.toHaveClass('is-disabled');
            submit_button.click();
            AjaxHelpers.respondWithJson(requests, {'success': true});
            expect(submit_button).toHaveClass('is-disabled');
        });

        it('It will not disable the submit button if there are errors in ajax request', function() {
            var requests = AjaxHelpers.requests(this);
            expect(submit_button).not.toHaveClass('is-disabled');
            submit_button.click();
            AjaxHelpers.respondWithError(requests, {});
            expect(submit_button).not.toHaveClass('is-disabled');
        });
    });
});
