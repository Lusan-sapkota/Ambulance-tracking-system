$(document).ready(function() {
    "use strict";

    // Animation for elements on page load
    $(window).on("load", function() {
        $(".header-text h2").addClass("animated fadeInUp").css({'animation-delay': '0.5s'});
        $(".header-text p").addClass("animated fadeInUp").css({'animation-delay': '1s'});
        $(".header-text a").addClass("animated fadeInDown").css({'animation-delay': '1.5s'});
    });

    // Function to handle active link based on hash
    function updateActiveLink() {
        var currentUrl = window.location.hash;  // Get the current URL hash (e.g., #about)
        console.log("Current URL Hash: " + currentUrl);  // Debugging the current hash

        // Reset all active classes by removing them
        $('.nav-link').removeClass('active');

        // Add the active class to the correct link based on the current URL hash
        if (currentUrl === '#welcome-hero') {
            $('#home-link').addClass('active');
        } else if (currentUrl === '#about') {
            $('#about-link').addClass('active');
        } else if (currentUrl === '#contact') {
            $('#contact-link').addClass('active');
        }
    }

    // Initial call to update the active link on page load
    updateActiveLink();

    // Listen for hash change events
    $(window).on('hashchange', function() {
        updateActiveLink();  // Call the function again if the hash changes
    });
});
