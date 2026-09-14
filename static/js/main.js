document.addEventListener("DOMContentLoaded", function () {
  // This ensures that the script runs only after the full HTML page has loaded.

  // Add smooth scrolling for internal links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      e.preventDefault(); // Prevent default jump behavior
      document.querySelector(this.getAttribute("href")).scrollIntoView({
        behavior: "smooth", // Enables smooth scrolling effect
      });
    });
  });

  // Add animation to paw print (Scroll to top when clicked)
  const pawPrint = document.querySelector(".paw-print");
  if (pawPrint) {
    pawPrint.addEventListener("click", () => {
      window.scrollTo({
        top: 0, // Scroll to the top of the page
        behavior: "smooth",
      });
    });
  }

  // Add selected class to choice buttons (for the questionnaire)
  const choiceButtons = document.querySelectorAll(".choice-btn");
  choiceButtons.forEach((button) => {
    button.addEventListener("click", function () {
      // Find the question card that contains this button
      const questionCard = this.closest(".question-card");

      // Remove 'selected' class from all other buttons in the same question
      questionCard.querySelectorAll(".choice-btn").forEach((btn) => {
        btn.classList.remove("selected");
      });

      // Add 'selected' class to the clicked button
      this.classList.add("selected");
    });
  });

  // Scroll to top button functionality
  const scrollTopBtn = document.getElementById("scrollTop");
  if (scrollTopBtn) {
    window.addEventListener("scroll", function () {
      // Show the button when user scrolls past 300px
      if (window.pageYOffset > 300) {
        scrollTopBtn.classList.add("visible");
      } else {
        scrollTopBtn.classList.remove("visible");
      }
    });

    // Scroll back to top when button is clicked
    scrollTopBtn.addEventListener("click", function () {
      window.scrollTo({
        top: 0, // Scroll to the top of the page
        behavior: "smooth",
      });
    });
  }

  console.log("JavaScript loaded successfully"); // Debugging log
});
