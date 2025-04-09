function setUpSlider() {
    const slider = document.getElementById('img-preview-slider');
    const prevButton = document.getElementById('slider-prev');
    const nextButton = document.getElementById('slider-next');

    const totalPreviews = slider.querySelectorAll('button').length;
  
    function slide(direction) {
        const currentPreview = slider.querySelector(`[aria-selected="true"]`);
        const currentPreviewIndex = parseInt(currentPreview.dataset.index);

        switch (direction) {
            case 'prev':
                nextIndex = Math.max(0, currentPreviewIndex - 1);
                break;
            case 'next':
            default:
                nextIndex = Math.min(totalPreviews, currentPreviewIndex + 1)
                break;
        }
  
        document.getElementById(`preview-${nextIndex}`).dispatchEvent(new Event('click'));
    }
  
    if (slider && prevButton && nextButton) {
        prevButton.addEventListener('click', () => slide('prev'));
        nextButton.addEventListener('click', () => slide('next'));
    }
}

function setUpCarousel() {
  const slider = document.getElementById("img-preview-slider");
  const totalPreviews = slider.querySelectorAll("button").length;
  const activeClassesPreview = ["border-4", "border-white", "pointer-events-none"];

  // TODO: Graceful shutdown if no images are available
  const previewWidth = slider.querySelectorAll("button")[0].offsetWidth;

  slider.querySelectorAll("button").forEach((imgPreview) => {
    imgPreview.addEventListener("click", (e) => {
      e.preventDefault();

      const clickedPreview = e.target.closest("button");
      const clickedTarget = document.getElementById(clickedPreview.getAttribute("aria-controls"));
      const clickedPreviewIndex = clickedPreview.dataset.index;

      console.debug(clickedPreviewIndex);

      const currentImage = document.getElementById("image-carousel").querySelector('[aria-selected="true"]');
      const currentPreview = slider.querySelector(`[aria-selected="true"]`);

      currentPreview.setAttribute("aria-selected", "false");
      currentPreview.classList.remove(...activeClassesPreview);

      currentImage.setAttribute("aria-selected", "false");
      currentImage.classList.add("hidden");

      // Set the clicked img to active
      clickedPreview.classList.add(...activeClassesPreview);
      clickedPreview.setAttribute("aria-selected", "true");

      clickedTarget.classList.remove("hidden");
      clickedTarget.setAttribute("aria-selected", "true");

      slider.scroll({
        left: clickedPreviewIndex * previewWidth - previewWidth,
        behavior: "smooth",
      });

      if (clickedPreviewIndex == 0) {
        document.getElementById("slider-prev").classList.add("hidden");
      } else if (clickedPreviewIndex == totalPreviews - 1) {
        document.getElementById("slider-next").classList.add("hidden");
      } else {
        document.getElementById("slider-prev").classList.remove("hidden");
        document.getElementById("slider-next").classList.remove("hidden");
      }
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
    setUpSlider();
    setUpCarousel();
});