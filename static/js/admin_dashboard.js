// Set the report download link and delete action when the modal is triggered
var deleteModal = document.getElementById('deleteModal');
deleteModal.addEventListener('show.bs.modal', function (event) {
    // Get the ID of the clicked delete button
    var button = event.relatedTarget; 
    var requestId = button.getAttribute('data-id'); // Get the request ID
    
    // Update the download link to point to the specific request ID
    var downloadLink = document.getElementById('download-link');
    downloadLink.href = '/download_pdf/' + requestId; // Correct route
    
    // Update the delete form action to point to the specific request ID
    var deleteForm = document.getElementById('delete-form-' + requestId);
    
    // Set the delete confirmation button to trigger form submission
    var deleteConfirmButton = document.getElementById('delete-confirm');
    deleteConfirmButton.onclick = function() {
        deleteForm.submit();
    }
});
