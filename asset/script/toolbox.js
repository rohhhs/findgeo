document.addEventListener('DOMContentLoaded', () => {
    let images = document.querySelectorAll('img.scale'); // Get all image elements
    var second_images = document.querySelectorAll('.scale > img');
    var combined_images = [...images , ...second_images];
    var set_combined_images = new Set(combined_images);
    
    set_combined_images.forEach(img => {
        img.addEventListener('click', () => {
            document.getElementById('media-fullscreen').classList.add('active');
            document.querySelector('#media-fullscreen > img').src = img.src;
        });
    });
});
async function shiftImage(el){
    console.log(event.target);
    if (!event.target.classList.contains('active')){
        el.querySelectorAll(".active").forEach(async (elem) => {
            elem.classList.remove('active')
        });
        event.target.classList.add('active');
        document.getElementById('image-preview').src = event.target.src;
    }
}