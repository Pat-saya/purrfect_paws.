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

  // Handle the questionnaire flow (displaying one question at a time)
  const questionnaireForm = document.querySelector("#questionnaireForm");
  if (questionnaireForm) {
    const questionCards = document.querySelectorAll(".question-card");
    let currentQuestionIndex = 0; // Keeps track of the current question being displayed

    // Function to show only one question at a time
    function showQuestion(index) {
      questionCards.forEach((card, i) => {
        if (i === index) {
          card.classList.remove("d-none"); // Show current question
        } else {
          card.classList.add("d-none"); // Hide other questions
        }
      });
    }

    // Function to check if a user has selected an answer before proceeding
    function isCurrentQuestionAnswered() {
      const currentCard = questionCards[currentQuestionIndex];
      return currentCard.querySelector(".choice-btn.selected") !== null;
    }

    // Ensure choice selection only allows one selected button per question
    document.querySelectorAll(".choice-btn").forEach((button) => {
      button.addEventListener("click", function () {
        const questionCard = this.closest(".question-card");
        questionCard.querySelectorAll(".choice-btn").forEach((btn) => {
          btn.classList.remove("selected"); // Remove 'selected' from all choices
        });
        this.classList.add("selected"); // Mark the clicked choice as selected
      });
    });

    // Handle clicking the "Next" button
    document.querySelectorAll(".next-btn").forEach((button) => {
      button.addEventListener("click", function () {
        if (!isCurrentQuestionAnswered()) {
          alert("Please select an answer before proceeding."); // Prevent proceeding if no answer is selected
          return;
        }
        currentQuestionIndex++; // Move to the next question
        showQuestion(currentQuestionIndex);
      });
    });

    // Handle clicking the "Previous" button
    document.querySelectorAll(".prev-btn").forEach((button) => {
      button.addEventListener("click", function () {
        currentQuestionIndex--; // Move to the previous question
        showQuestion(currentQuestionIndex);
      });
    });

    // Handle form submission
    questionnaireForm.addEventListener("submit", async function (e) {
      e.preventDefault(); // Prevent the default form submission behavior
      console.log("Form submitted"); // Debugging log

      // Ensure all questions have been answered
      const unansweredQuestions = Array.from(questionCards).filter(
        (card) => !card.querySelector(".choice-btn.selected")
      );

      if (unansweredQuestions.length > 0) {
        alert("Please answer all questions before submitting.");
        return;
      }

      // Collect the user's answers
      const answers = {};
      questionCards.forEach((card) => {
        const selectedButton = card.querySelector(".choice-btn.selected");
        if (selectedButton) {
          const questionId = card.dataset.questionId; // Retrieve question ID
          const choiceId = selectedButton.dataset.choiceId; // Retrieve selected choice ID
          console.log(`Question ${questionId}: selected choice ${choiceId}`); // Debug log
          answers[questionId] = parseInt(choiceId);
        }
      });

      console.log("Submitting answers:", answers);

      try {
        // Send answers to the server via API request
        const response = await fetch("/api/questionnaire", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector('meta[name="csrf-token"]')
              .content,
          },
          body: JSON.stringify({ answers: answers }), // Convert answers to JSON
        });

        console.log("Response status:", response.status); // Debugging log

        const data = await response.json();
        console.log("Response data:", data); // Debugging log

        // Always redirect to results page
        window.location.href = "/results";
      } catch (error) {
        console.error("Error:", error);
        window.location.href = "/results"; // Still redirect even if there's an error
      }
    });
  }

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
