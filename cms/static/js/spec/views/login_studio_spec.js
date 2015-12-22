define(['jquery', 'js/factories/login', 'common/js/spec_helpers/ajax_helpers', 'common/js/components/utils/view_utils'],
function($, LoginFactory, AjaxHelpers, ViewUtils) {
    'use strict';
    describe("Studio Login Page", function() {
        var submit_button;

        beforeEach(function() {
            loadFixtures('login.underscore');
            /*jshint unused: false*/
            var login_factory = new LoginFactory("/home/");
            submit_button = $('#submit');
        });

        it('It will disable the submit button once it is clicked', function() {
            spyOn(ViewUtils, 'redirect').andCallFake(function(){});
            var addClassSpy = spyOn($.fn, 'addClass').andReturn(submit_button);
            spyOn($.fn, 'removeClass').andReturn(submit_button);
            var requests = AjaxHelpers.requests(this);
            submit_button.click();
            expect($.fn.addClass).toHaveBeenCalledWith('is-disabled');
            expect(addClassSpy.mostRecentCall.object.selector).toEqual('#submit');
            AjaxHelpers.respondWithJson(requests, {'success': true});
            expect($.fn.removeClass).not.toHaveBeenCalled();
        });

        it('It will not disable the submit button if there are errors in ajax request', function() {
            var requests = AjaxHelpers.requests(this);
            var addClassSpy = spyOn($.fn, 'addClass').andReturn(submit_button);
            var removeClassSpy = spyOn($.fn, 'removeClass').andReturn(submit_button);
            submit_button.click();
            expect($.fn.addClass).toHaveBeenCalledWith('is-disabled');
            expect(addClassSpy.mostRecentCall.object.selector).toEqual('#submit');
            AjaxHelpers.respondWithError(requests, {});
            expect($.fn.removeClass).toHaveBeenCalledWith('is-disabled');
            expect(removeClassSpy.mostRecentCall.object.selector).toEqual('#submit');
        });
    });
});
