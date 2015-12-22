/*global define */
define([
        'jquery',
        'common/js/spec_helpers/ajax_helpers',
        'js/certificates/models/certificate_invalidation',
        'js/certificates/views/certificate_invalidation_view',
        'js/certificates/collections/certificate_invalidation_collection'
    ],
    function($, AjaxHelpers, CertificateInvalidationModel, CertificateInvalidationView,
             CertificateInvalidationCollection) {
        'use strict';
        describe("edx.certificates.models.certificate_invalidation.CertificateInvalidationModel", function() {
            var certificate_invalidation = null;
            var assertValid = function(fields, isValid, expectedErrors) {
                certificate_invalidation.set(fields);
                var errors = certificate_invalidation.validate(certificate_invalidation.attributes);

                if (isValid) {
                    expect(errors).toBe(undefined);
                } else {
                    expect(errors).toEqual(expectedErrors);
                }
            };

            var EXPECTED_ERRORS = {
                user_name_or_email_required: 'Student username/email field is required and can not be empty. ' +
                'Kindly fill in username/email and then press "Invalidate Certificate" button.'
            };

            beforeEach(function() {

                certificate_invalidation = new CertificateInvalidationModel({user_name: 'test_user'});
                certificate_invalidation.set({
                    notes: "Test notes"
                });
            });

            it("accepts valid email addresses", function() {
                assertValid({user_email: "bob@example.com"}, true);
                assertValid({user_email: "bob+smith@example.com"}, true);
                assertValid({user_email: "bob+smith@example.com"}, true);
                assertValid({user_email: "bob+smith@example.com"}, true);
                assertValid({user_email: "bob@test.example.com"}, true);
                assertValid({user_email: "bob@test-example.com"}, true);
            });

            it("displays username or email required error", function() {
                assertValid({user_name: ""}, false, EXPECTED_ERRORS.user_name_or_email_required);
            });
        });

        describe("edx.certificates.collections.certificate_invalidation_collection.CertificateInvalidationCollection",
            function() {
                var certificate_invalidations = null,
                    certificate_invalidation_url = 'test/url/';
                var certificate_invalidations_json = [
                    {
                        id: 1,
                        user_name: "test1",
                        user_email: "test1@test.com",
                        invalidated_by: 2,
                        created: "Thursday, October 29, 2015",
                        notes: "test notes for test certificate invalidation"
                    },
                    {
                        id: 2,
                        user_name: "test2",
                        user_email : "test2@test.com",
                        invalidated_by: 2,
                        created: "Thursday, October 29, 2015",
                        notes: "test notes for test certificate invalidation"
                    }
                ];

                beforeEach(function() {
                    certificate_invalidations = new CertificateInvalidationCollection(certificate_invalidations_json, {
                        parse: true,
                        canBeEmpty: true,
                        url: certificate_invalidation_url
                    });
                });

                it("has 2 models in the collection after initialization", function() {
                    expect(certificate_invalidations.models.length).toEqual(2);
                });

                it("model is removed from collection on destroy", function() {
                    var model = certificate_invalidations.get({id: 2});
                    model.destroy();
                    expect(certificate_invalidations.models.length).toEqual(1);
                    expect(certificate_invalidations.get({id: 2})).toBe(undefined);
                });
            }
        );

        describe("edx.certificates.views.certificate_invalidation_view.CertificateInvalidationView", function() {
            var view = null,
                certificate_invalidation_url = 'test/url/',
                user_name_field = null,
                notes_field = null,
                invalidate_button=null,
                duplicate_user='test2@test.com',
                new_user='test4@test.com',
                requests=null;

                var messages = {
                    error: {
                        empty_user_name_email: 'Student username/email field is required and can not be empty. ' +
                        'Kindly fill in username/email and then press "Invalidate Certificate" button.',
                        duplicate_user: "Certificate of " + (duplicate_user) + " has already been invalidated. " +
                        "Please check your spelling and retry.",
                        server_error: "Server Error, Please refresh the page and try again.",
                        from_server: "Test Message from server"
                    },
                    success: {
                        saved: "Certificate has been successfully invalidated for " + new_user + '.',
                        re_validated: 'The certificate for this learner has been re-validated and ' +
                        'the system is re-running the grade for this learner.'
                    }
                };

            var certificate_invalidations_json = [
                {
                    id: 1,
                    user_name: "test1",
                    user_email: "test1@test.com",
                    invalidated_by: 2,
                    created: "Thursday, October 29, 2015",
                    notes: "test notes for test certificate invalidation"
                },
                {
                    id: 2,
                    user_name: "test2",
                    user_email : "test2@test.com",
                    invalidated_by: 2,
                    created: "Thursday, October 29, 2015",
                    notes: "test notes for test certificate invalidation"
                }
            ];

            beforeEach(function() {
                setFixtures();
                var fixture =readFixtures(
                    "templates/instructor/instructor_dashboard_2/certificate-invalidation.underscore"
                );

                setFixtures(
                    "<div class='certificate-invalidation-container'>" +
                    "   <h2>Invalidate Certificates</h2> " +
                    "   <div id='certificate-invalidation'></div>" +
                    "</div>" +
                    "<script type='text/template' id='certificate-invalidation-tpl'>" + fixture + "</script>"
                );

                var certificate_invalidations = new CertificateInvalidationCollection(certificate_invalidations_json, {
                    parse: true,
                    canBeEmpty: true,
                    url: certificate_invalidation_url,
                    generate_certificates_url: certificate_invalidation_url

                });

                view = new CertificateInvalidationView({collection: certificate_invalidations});
                view.render();

                user_name_field = $("#certificate-invalidation-user");
                notes_field = $("#certificate-invalidation-notes");
                invalidate_button = $("#invalidate-certificate");

                requests = AjaxHelpers.requests(this);
            });

            it("verifies view is initialized and rendered successfully", function() {
                expect(view).not.toBe(undefined);
                expect(view.$el.find('table tbody tr').length).toBe(2);
            });

            it("verifies view is rendered on add/remove to collection", function() {
                var user = 'test3',
                    notes = 'test3 notes',
                    model = new CertificateInvalidationModel({user_name: user, notes: notes});

                // Add another model in collection and verify it is rendered
                view.collection.add(model);
                expect(view.$el.find('table tbody tr').length).toBe(3);

                expect(view.$el.find('table tbody tr td:contains("' + user + '")').parent().html()).
                    toMatch(notes);
                expect(view.$el.find('table tbody tr td:contains("' + user + '")').parent().html()).
                    toMatch(user);

                // Remove a model from collection
                var collection_model = view.collection.get({id: 2});
                collection_model.destroy();

                // Verify view is updated
                expect(view.$el.find('table tbody tr').length).toBe(2);


            });

            it("verifies view error message on duplicate certificate validation.", function() {
                $(user_name_field).val(duplicate_user);
                $(invalidate_button).click();

                expect($("#certificate-invalidation div.message").text()).toEqual(messages.error.duplicate_user);
            });

            it("verifies view error message on empty username/email field.", function() {
                $(user_name_field).val("");
                $(invalidate_button).click();

                expect($("#certificate-invalidation div.message").text()).toEqual(messages.error.empty_user_name_email);
            });

            it("verifies view success message on certificate invalidation.", function() {
                $(user_name_field).val(new_user);
                $(notes_field).val("test notes for user test4");
                $(invalidate_button).click();

                AjaxHelpers.respondWithJson(
                    requests,
                    {
                        id: 4,
                        user_name: 'test4',
                        user_email : new_user,
                        validated_by: 5,
                        created: "Thursday, December 29, 2015",
                        notes: "test notes for user test4"
                    }
                );
                expect($("#certificate-invalidation div.message").text()).toEqual(messages.success.saved);
            });

            it("verifies view server error if server returns unknown response.", function() {
                $(user_name_field).val(new_user);
                $(notes_field).val("test notes for user test4");
                $(invalidate_button).click();

                // Response with empty body
                AjaxHelpers.respondWithTextError(requests, 400, "");

                expect($("#certificate-invalidation div.message").text()).toEqual(messages.error.server_error);
            });

            it("verifies certificate re-validation request and success message.", function() {
                var user_name = 'test1',
                    re_validate_certificate = "div.certificate-invalidation-container table tr:contains('" + 
                        user_name + "') td .re-validate-certificate";

                $(re_validate_certificate).click();
                AjaxHelpers.respondWithJson(requests, {});

                expect($("#certificate-invalidation div.message").text()).toEqual(messages.success.re_validated);
            });

            it("verifies error message from server is displayed.", function() {
                var user_name = 'test1',
                    re_validate_certificate = "div.certificate-invalidation-container table tr:contains('" +
                        user_name + "') td .re-validate-certificate";

                $(re_validate_certificate).click();
                AjaxHelpers.respondWithError(requests, 400, {
                    success: false,
                    message: messages.error.from_server
                });

                expect($("#certificate-invalidation div.message").text()).toEqual(messages.error.from_server);
            });

        });
    }
);
